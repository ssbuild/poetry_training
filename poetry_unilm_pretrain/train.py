# -*- coding: utf-8 -*-
import os

import numpy as np
import torch
from deep_training.data_helper import ModelArguments, DataArguments, TrainingArguments
from deep_training.nlp.models.transformer import TransformerModelForUnilm, TransformerLightningModule
from deep_training.utils.trainer import SimpleModelCheckpoint
from lightning import Trainer
from torch.utils.data import DataLoader, IterableDataset
from transformers import HfArgumentParser, BertTokenizer
from data_utils import NN_DataHelper, data_conf,train_info_args




class MyTransformer(TransformerModelForUnilm, with_pl=True):
    def __init__(self, *args, **kwargs):
        super(MyTransformer, self).__init__(*args, **kwargs)


class MySimpleModelCheckpoint(SimpleModelCheckpoint):
    def __init__(self, *args, **kwargs):
        super(MySimpleModelCheckpoint, self).__init__(*args, **kwargs)
        self.weight_file = './best.pt'

    @staticmethod
    def generate_text(pl_module: MyTransformer, prefix, tokenizer, max_target_length, device=0):
        device = torch.device('cuda:{}'.format(device))
        # 简易测试生成
        o = tokenizer.encode_plus(prefix, truncation=True, max_length=512, return_attention_mask=False)
        gen_ids, gen_tokens = [], []
        batch = {}
        for i in range(max_target_length):
            batch.clear()
            batch['input_ids'] = [o['input_ids'] + gen_ids]
            batch['token_type_ids'] = [o['token_type_ids'] + [1] * len(gen_ids) ]
            for k in batch:
                batch[k] = torch.tensor(batch[k], dtype=torch.int32)
            for k in batch:
                batch[k] = batch[k].to(device)
            out = pl_module.test_step(batch, 0)
            logits = out['outputs'][0]
            logits = np.argmax(logits[:, -1], axis=-1)
            logits = logits[0]
            gen_ids.append(logits)
            token = tokenizer._convert_id_to_token(logits)
            if token.startswith('##'):
                token = token.replace('##', '')
            gen_tokens.append(token)
        return ''.join(gen_tokens)


    def on_save_model(
            self, trainer: "pl.Trainer", pl_module: "pl.LightningModule"
    ) -> None:
        # 保存权重
        super(MySimpleModelCheckpoint, self).on_save_model(trainer, pl_module)
        special = data_conf['special']
        prefixs = [('七律', '归山吟寄友'),
                   ('五绝', '钓鱼有感'),
                   ('对联', '五湖四海'),
                   ('歌词', '风雨'),
                   ('骂人', ''),
                   ('成语', ''),
                   ('当代', ''),
                   ('曲', ''),
                   ('五律', ''),
                   ('七律', ''),
                   ('姓名', ''),
                   ]
        print('*' * 30)
        device = trainer.global_rank
        self.tokenizer: BertTokenizer
        tokenizer = self.tokenizer
        data_args = self.data_args
        for prefix in prefixs:
            print(prefix[0], prefix[1])
            prefix = special[prefix[0]] + prefix[1]
            output = MySimpleModelCheckpoint.generate_text(pl_module, prefix, tokenizer,
                                                           data_args.max_target_length, device=device)
            print('input', prefix)
            print('output', output)
            print()



if __name__ == '__main__':
    parser = HfArgumentParser((ModelArguments, TrainingArguments, DataArguments))
    model_args, training_args, data_args = parser.parse_dict(train_info_args)
    # 保存最小loss模型
    checkpoint_callback = MySimpleModelCheckpoint(every_n_train_steps=2000 // training_args.gradient_accumulation_steps,
        # monitor="loss",
                                                  )
    trainer = Trainer(
        callbacks=[checkpoint_callback],
        max_epochs=training_args.max_epochs,
        max_steps=training_args.max_steps,
        accelerator="gpu",
        devices=data_args.devices,
        enable_progress_bar=True,
        default_root_dir=data_args.output_dir,
        gradient_clip_val=training_args.max_grad_norm,
        accumulate_grad_batches=training_args.gradient_accumulation_steps,
        num_sanity_val_steps=0,
        strategy='ddp' if torch.cuda.device_count() > 1 else 'auto',
    )

    dataHelper = NN_DataHelper(model_args, training_args, data_args)
    tokenizer, config, label2id, id2label = dataHelper.load_tokenizer_and_config()

    # 额外参数
    checkpoint_callback.tokenizer = tokenizer
    checkpoint_callback.data_args = data_args

    # 缓存数据集
    if data_args.do_train:
        dataHelper.make_dataset_with_args(data_args.train_file,mixed_data=False,shuffle=True,mode='train')
    if data_args.do_eval:
        dataHelper.make_dataset_with_args(data_args.eval_file, mode='eval')
    if data_args.do_test:
        dataHelper.make_dataset_with_args(data_args.test_file,mode='test')



    model = MyTransformer(ignore_index=config.pad_token_id,config=config, model_args=model_args, training_args=training_args)

    if not data_args.convert_onnx:
        # 加载数据
        train_datasets = dataHelper.load_distributed_random_sampler(
            dataHelper.train_files,
            with_load_memory=True,
            collate_fn=dataHelper.collate_fn,
            batch_size=training_args.train_batch_size,
            num_processes = trainer.world_size, process_index=trainer.global_rank)
        ckpt_path = './best.pt'
        if not os.path.exists(ckpt_path):
            ckpt_path = None
        if train_datasets is not None:
            trainer.fit(model, train_dataloaders=train_datasets, ckpt_path=ckpt_path)
        else:
            eval_datasets = dataHelper.load_sequential_sampler(dataHelper.eval_files,batch_size=training_args.eval_batch_size,collate_fn=dataHelper.collate_fn)
            test_datasets = dataHelper.load_sequential_sampler(dataHelper.test_files,batch_size=training_args.test_batch_size,collate_fn=dataHelper.collate_fn)
            if eval_datasets is not None:
                trainer.validate(model, dataloaders=eval_datasets, ckpt_path='./best.pt')

            if test_datasets is not None:
                trainer.test(model, dataloaders=test_datasets, ckpt_path='best.pt')
    else:
        # 加载权重
        model = MyTransformer.load_from_checkpoint('./best.pt',
                                                   ignore_index=config.pad_token_id,
                                                   config=config, model_args=model_args,
                                                   training_args=training_args)
        input_sample = (
                           ("input_ids", torch.ones(size=(1, 128), dtype=torch.int32)),
                           ("token_type_ids", torch.ones(size=(1, 128), dtype=torch.int32)),
                       )
        input_names = ("input_ids", "token_type_ids")
        output_names = ("pred_ids",)
        dynamic_axes = None or {"input_ids": [0, 1], "token_type_ids": [0, 1], "pred_ids": [0, 1]}
        model.convert_to_onnx('./best.onnx',
                              input_sample=input_sample,
                              input_names=input_names,
                              output_names=output_names,
                              dynamic_axes=dynamic_axes)


