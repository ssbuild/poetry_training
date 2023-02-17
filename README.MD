## 安装

- pip install -U deep_training >= 0.0.14
- 当前文档版本pypi 0.0.14

## 更新详情

- [deep_training](https://github.com/ssbuild/deep_training)

## 深度学习常规任务例子

- [deep_training-examples](https://github.com/ssbuild/deep_training-examples)

## 支持模型

    gpt2 
    laMDA
    PaLM
    t5
    unilm
    t5decoder


## 导出onnx模型 通常只需要三步

    第一步，参数配置 convert_onnx = True
    第二步 加载权重例子
    model = MyTransformer.load_from_checkpoint('./best.pt', config=config, model_args=model_args,
                                                   training_args=training_args)
    第三步 #导出onnx模型
    model.convert_to_onnx('./best.onnx')

## 多卡训练策略 strategy , 通常只需要一步
    修改参数配置 devices = N 

    # Available names: bagua, colossalai, ddp, ddp_find_unused_parameters_false, ddp_fork,
    # ddp_fork_find_unused_parameters_false, ddp_fully_sharded,
    # ddp_notebook, ddp_notebook_find_unused_parameters_false, ddp_sharded,
    # ddp_sharded_find_unused_parameters_false, ddp_sharded_spawn,
    # ddp_sharded_spawn_find_unused_parameters_false,
    # ddp_spawn, ddp_spawn_find_unused_parameters_false,
    # deepspeed, deepspeed_stage_1, deepspeed_stage_2, deepspeed_stage_2_offload,
    # deepspeed_stage_3, deepspeed_stage_3_offload, deepspeed_stage_3_offload_nvme,
    # dp, fsdp, fsdp_native, fsdp_native_full_shard_offload, horovod, hpu_parallel,
    # hpu_single, ipu_strategy, single_device, single_tpu, tpu_spawn, tpu_spawn_debug"

## 愿景

创建一个模型工厂, 轻量且高效的训练程序，让训练模型更容易,更轻松上手。

## 交流

QQ交流群：185144988
