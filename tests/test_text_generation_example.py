import json
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pytest

from .test_examples import TIME_PERF_FACTOR


prev_quant_model_name = None
prev_quant_rank = 0

if os.environ.get("GAUDI2_CI", "0") == "1":
    # Gaudi2 CI baselines
    MODELS_TO_TEST = {
        "bf16_1x": [
            ("bigscience/bloomz-7b1", 1, False, 130.0472971205316),
            ("gpt2-xl", 1, False, 281.8734689674413),
            ("EleutherAI/gpt-j-6b", 1, False, 160.5823842101192),
            ("EleutherAI/gpt-neox-20b", 1, False, 50.67672679310354),
            ("meta-llama/Llama-2-7b-hf", 1, True, 141.25776956002076),
            ("tiiuae/falcon-40b", 1, True, 25.202450111088346),
            ("bigcode/starcoder", 256, True, 6846.575763562658),
            ("Salesforce/codegen2-1B", 1, False, 446.4029486883532),
            ("mosaicml/mpt-30b", 1, False, 36.06464336116623),
            ("mistralai/Mistral-7B-v0.1", 1, True, 130.2172236767782),
            ("mistralai/Mixtral-8x7B-v0.1", 1, False, 23.7931001677926),
            ("microsoft/phi-2", 1, False, 224.72307766211117),
            ("meta-llama/Meta-Llama-3-8B", 1, True, 129),
            ("meta-llama/Llama-2-7b-hf", 512, True, 12808),
            ("meta-llama/Llama-2-7b-hf", 512, False, 8711),  # in some cases like TGI, reuse_cache isnt used
            ("stabilityai/stablelm-2-12b", 1, False, 74.8904496532218),
            ("codellama/CodeLlama-34b-hf", 1, True, 32.644),
            ("bigcode/starcoder2-3b", 1, False, 261.07213776344133),
            ("adept/persimmon-8b-base", 4, False, 366.73968820698406),
            ("Qwen/Qwen1.5-7B", 4, False, 490.8621617893209),
            ("google/gemma-7b", 1, False, 109.70751574382221),
            ("state-spaces/mamba-130m-hf", 1536, False, 5385.511100161605),
            ("Deci/DeciLM-7B", 1, False, 120),
            ("Qwen/Qwen2-7B", 512, False, 9669.45787),
            ("Qwen/Qwen1.5-MoE-A2.7B", 1, True, 44.25834541569395),
            ("EleutherAI/gpt-neo-2.7B", 1, False, 257.2476416844122),
            ("facebook/xglm-1.7B", 1, False, 357.46365062825083),
            ("CohereForAI/c4ai-command-r-v01", 1, False, 29.50315234651154),
        ],
        "fp8": [
            ("tiiuae/falcon-180B", 4, 950, True, 128, 128, 2506.68),
            ("meta-llama/Llama-2-7b-hf", 1, 1230, False, 128, 128, 13152.7),
            ("meta-llama/Llama-2-7b-hf", 1, 163, False, 128, 2048, 4774.7),
            ("meta-llama/Llama-2-7b-hf", 1, 94, False, 2048, 128, 1293.3),
            ("meta-llama/Llama-2-7b-hf", 1, 81, False, 2048, 2048, 1942.9),
            ("meta-llama/Llama-2-70b-hf", 4, 3042, False, 128, 128, 5374.6),
            ("meta-llama/Llama-2-70b-hf", 4, 750, False, 128, 2048, 7422.4),
            ("meta-llama/Llama-2-70b-hf", 4, 207, False, 2048, 128, 568.5),
            ("meta-llama/Llama-2-70b-hf", 8, 172, False, 2048, 2048, 4656.2),
            ("mistralai/Mistral-7B-Instruct-v0.2", 1, 896, True, 128, 128, 17068.965283763682),
            ("mistralai/Mistral-7B-Instruct-v0.2", 1, 120, True, 128, 2048, 6979.225194247115),
            ("mistralai/Mistral-7B-Instruct-v0.2", 1, 120, True, 2048, 128, 1681.4401450088983),
            ("mistralai/Mistral-7B-Instruct-v0.2", 1, 44, True, 2048, 2048, 3393.149396451692),
            ("mistralai/Mixtral-8x7B-v0.1", 1, 1, True, 128, 128, 40.94),
            ("mistralai/Mixtral-8x7B-v0.1", 2, 768, True, 128, 128, 3428.65),
            ("mistralai/Mixtral-8x7B-v0.1", 2, 96, True, 128, 2048, 2570.34),
            ("mistralai/Mixtral-8x7B-v0.1", 2, 96, True, 2048, 128, 379.03),
            ("mistralai/Mixtral-8x7B-v0.1", 2, 48, True, 2048, 2048, 1147.50),
            ("microsoft/phi-2", 1, 1, True, 128, 128, 254.08932787178165),
        ],
        "load_quantized_model_with_autogptq": [
            ("TheBloke/Llama-2-7b-Chat-GPTQ", 1, 10, False, 128, 2048, 456.7),
        ],
        "deepspeed": [
            ("bigscience/bloomz", 8, 1, 36.77314954096159),
            ("meta-llama/Llama-2-70b-hf", 8, 1, 64.10514998902435),
            ("meta-llama/Meta-Llama-3-70B-Instruct", 8, 1, 64),
            ("facebook/opt-66b", 2, 1, 28.48069266504111),
        ],
        "torch_compile": [
            ("meta-llama/Llama-2-7b-hf", 102.27823420713148),
        ],
        "torch_compile_distributed": [
            ("meta-llama/Llama-2-7b-hf", 39.72973199515235),
        ],
        "distributed_tp": [
            ("meta-llama/Llama-2-7b-hf", 1345.2369318328463),
        ],
        "contrastive_search": [
            ("gpt2-xl", 1, False, 51.61471298016438),
        ],
    }
else:
    # Gaudi1 CI baselines
    MODELS_TO_TEST = {
        "bf16_1x": [
            ("bigscience/bloomz-7b1", 1, False, 41.7555095197846),
            ("gpt2-xl", 1, False, 142.11481820425706),
            # TODO: fix OPT 6.7B
            # ("facebook/opt-6.7b", 0.0),
            ("EleutherAI/gpt-j-6b", 1, True, 156.2893125740893),
            ("meta-llama/Llama-2-7b-hf", 1, True, 44.39616259946937),
            ("tiiuae/falcon-7b", 1, True, 44.82870145718665),
            ("bigcode/starcoder", 1, False, 15.945023767901013),
            ("Salesforce/codegen2-1B", 1, False, 155.32071248826423),
            ("mosaicml/mpt-7b", 1, False, 45.45168927038262),
            ("mistralai/Mistral-7B-v0.1", 1, True, 41.21906841459711),
            ("microsoft/phi-2", 1, False, 92.53083167241344),
            ("google/gemma-7b", 1, False, 28.84284625836978),
            ("stabilityai/stablelm-2-12b", 1, False, 26.80858949645992),
            ("Qwen/Qwen1.5-7B", 1, False, 39.29068423087616),
            ("adept/persimmon-8b-base", 1, False, 34.53559807384106),
            ("bigcode/starcoder2-3b", 1, False, 82.09655684566117),
            ("state-spaces/mamba-130m-hf", 224, False, 794.542),
        ],
        "fp8": [],
        "load_quantized_model_with_autogptq": [],
        "deepspeed": [
            ("bigscience/bloomz-7b1", 8, 1, 31.994268212011505),
        ],
        "torch_compile": [],
        "torch_compile_distributed": [],
        "distributed_tp": [],
        "contrastive_search": [
            ("gpt2-xl", 1, False, 34.48141280163397),
        ],
    }


def _test_text_generation(
    model_name: str,
    baseline: float,
    token: str,
    batch_size: int = 1,
    reuse_cache: bool = False,
    deepspeed: bool = False,
    world_size: int = 8,
    torch_compile: bool = False,
    fp8: bool = False,
    load_quantized_model_with_autogptq: bool = False,
    max_input_tokens: int = 0,
    max_output_tokens: int = 100,
    parallel_strategy: str = None,
    contrastive_search: bool = False,
):
    command = ["python3"]
    path_to_example_dir = Path(__file__).resolve().parent.parent / "examples"
    env_variables = os.environ.copy()

    if deepspeed:
        command += [
            f"{path_to_example_dir / 'gaudi_spawn.py'}",
            "--use_deepspeed",
            f"--world_size {world_size}",
        ]
    elif parallel_strategy == "tp":
        command += [
            f"{path_to_example_dir / 'gaudi_spawn.py'}",
            f"--world_size {world_size}",
        ]

    command += [
        f"{path_to_example_dir / 'text-generation' / 'run_generation.py'}",
        f"--model_name_or_path {model_name}",
        f"--batch_size {batch_size}",
        "--use_kv_cache",
        f"--max_new_tokens {max_output_tokens}",
    ]

    is_starcoder_first_gen_model = "starcoder" in model_name.lower() and "starcoder2" not in model_name.lower()

    if "llama" in model_name.lower():
        command += ["--trim_logits", "--attn_softmax_bf16"]

    if "falcon" in model_name.lower() or "starcoder2" in model_name.lower():
        command += ["--use_flash_attention", "--flash_attention_causal_mask"]

    if is_starcoder_first_gen_model:
        command += ["--use_flash_attention"]

        # starcoder doesn't support reuse_cache, but implements bucket_internal instead
        if reuse_cache:
            command += ["--bucket_size 128"]
            command += ["--bucket_internal"]

    if "starcoder2" in model_name.lower():
        command += ["--flash_attention_recompute"]

    if "gemma" in model_name.lower():
        command += ["--use_flash_attention"]

    if (reuse_cache or torch_compile) and not parallel_strategy == "tp" and not is_starcoder_first_gen_model:
        command += ["--reuse_cache"]

    if torch_compile:
        command += ["--torch_compile"]
        if parallel_strategy == "tp":
            command += ["--use_flash_attention"]
            command += ["--flash_attention_recompute"]
        env_variables["PT_ENABLE_INT64_SUPPORT"] = "1"
        env_variables["PT_HPU_LAZY_MODE"] = "0"
    else:
        command += [
            "--use_hpu_graphs",
        ]

    if not deepspeed:
        command.append("--bf16")

    if contrastive_search:
        command += ["--top_k 4", "--penalty_alpha 0.5"]

    if fp8:
        if "--trim_logits" not in command:
            command += ["--trim_logits"]
        if "Llama-2" in model_name:
            command.insert(-2, "--use_flash_attention")
            command.insert(-2, "--flash_attention_recompute")
            command.insert(-2, "--bucket_size 128")
            command.insert(-2, "--bucket_internal")
        if "Mistral" in model_name:
            command.insert(-2, "--use_flash_attention")
            command.insert(-2, "--flash_attention_recompute")
            command.insert(-2, "--attn_softmax_bf16")
            command.insert(-2, "--trim_logits")
        if "Mixtral" in model_name:
            command.insert(-2, "--bucket_size 128")
            command.insert(-2, "--bucket_internal")
        elif "falcon-180b" in model_name.lower():
            command.insert(-2, "--flash_attention_recompute")

        global prev_quant_model_name
        global prev_quant_rank
        measure_command = None
        # FP8 Measurement only needed
        if (prev_quant_model_name is None) or (prev_quant_model_name != model_name) or (prev_quant_rank != world_size):
            measure_command = [
                x for x in command if not x.startswith("--max_new_tokens")
            ]  # Remove max_new_tokens for measurement
            measure_command = [
                x if not x.startswith("--batch_size") else "--batch_size 1" for x in measure_command
            ]  # Remove batch_size for measurement

            prev_quant_model_name = model_name
            prev_quant_rank = world_size

        # FP8 text generation
        command += [
            f"--max_input_tokens {max_input_tokens}",
            "--limit_hpu_graphs",
        ]
    if load_quantized_model_with_autogptq:
        command += ["--load_quantized_model_with_autogptq"]
    if parallel_strategy is not None:
        command += [
            f"--parallel_strategy={parallel_strategy}",
        ]

    with TemporaryDirectory() as tmp_dir:
        command.append(f"--output_dir {tmp_dir}")
        command.append(f"--token {token.value}")

        pattern = re.compile(r"([\"\'].+?[\"\'])|\s")

        if fp8:
            env_variables["TQDM_DISABLE"] = "1"
            if measure_command is not None:
                measure_command.append(f"--token {token.value}")
                env_variables["QUANT_CONFIG"] = os.path.join(
                    path_to_example_dir, "text-generation/quantization_config/maxabs_measure_include_outputs.json"
                )
                measure_command = [x for y in measure_command for x in re.split(pattern, y) if x]
                print(f"\n\nMeasure Command to test: {' '.join(measure_command[:-2])}\n")
                proc = subprocess.run(measure_command, env=env_variables)

                # Ensure the run finished without any issue
                # Use try-except to avoid logging the token if used
                try:
                    assert proc.returncode == 0
                except AssertionError as e:
                    if "'--token', 'hf_" in e.args[0]:
                        e.args = (f"The following command failed:\n{' '.join(measure_command[:-2])}",)
                    raise

            if "Mixtral" in model_name:
                env_variables["QUANT_CONFIG"] = os.path.join(
                    path_to_example_dir, "text-generation/quantization_config/maxabs_quant_mixtral.json"
                )
            else:
                env_variables["QUANT_CONFIG"] = os.path.join(
                    path_to_example_dir, "text-generation/quantization_config/maxabs_quant.json"
                )

        command = [x for y in command for x in re.split(pattern, y) if x]
        print(f"\n\nCommand to test: {' '.join(command[:-2])}\n")
        proc = subprocess.run(command, env=env_variables)

        # Ensure the run finished without any issue
        # Use try-except to avoid logging the token if used
        try:
            assert proc.returncode == 0
        except AssertionError as e:
            if "'--token', 'hf_" in e.args[0]:
                e.args = (f"The following command failed:\n{' '.join(command[:-2])}",)
            raise

        with open(Path(tmp_dir) / "results.json") as fp:
            results = json.load(fp)

        # Ensure performance requirements (throughput) are met
        assert results["throughput"] >= (2 - TIME_PERF_FACTOR) * baseline


@pytest.mark.parametrize("model_name, batch_size, reuse_cache, baseline", MODELS_TO_TEST["bf16_1x"])
def test_text_generation_bf16_1x(model_name: str, baseline: float, batch_size: int, reuse_cache: bool, token: str):
    _test_text_generation(model_name, baseline, token, batch_size, reuse_cache)


@pytest.mark.parametrize(
    "model_name, world_size, batch_size, reuse_cache, input_len, output_len, baseline", MODELS_TO_TEST["fp8"]
)
def test_text_generation_fp8(
    model_name: str,
    baseline: float,
    world_size: int,
    batch_size: int,
    reuse_cache: bool,
    input_len: int,
    output_len: int,
    token: str,
):
    deepspeed = True if world_size > 1 else False
    _test_text_generation(
        model_name,
        baseline,
        token,
        deepspeed=deepspeed,
        world_size=world_size,
        fp8=True,
        batch_size=batch_size,
        reuse_cache=reuse_cache,
        max_input_tokens=input_len,
        max_output_tokens=output_len,
    )


@pytest.mark.parametrize(
    "model_name, world_size, batch_size, reuse_cache, input_len, output_len, baseline",
    MODELS_TO_TEST["load_quantized_model_with_autogptq"],
)
def test_text_generation_gptq(
    model_name: str,
    baseline: float,
    world_size: int,
    batch_size: int,
    reuse_cache: bool,
    input_len: int,
    output_len: int,
    token: str,
):
    deepspeed = True if world_size > 1 else False
    _test_text_generation(
        model_name,
        baseline,
        token,
        deepspeed=deepspeed,
        world_size=world_size,
        fp8=False,
        load_quantized_model_with_autogptq=True,
        batch_size=batch_size,
        reuse_cache=reuse_cache,
        max_input_tokens=input_len,
        max_output_tokens=output_len,
    )


@pytest.mark.parametrize("model_name,  world_size, batch_size, baseline", MODELS_TO_TEST["deepspeed"])
def test_text_generation_deepspeed(model_name: str, baseline: float, world_size: int, batch_size: int, token: str):
    _test_text_generation(model_name, baseline, token, deepspeed=True, world_size=world_size, batch_size=batch_size)


@pytest.mark.parametrize("model_name, baseline", MODELS_TO_TEST["torch_compile"])
def test_text_generation_torch_compile(model_name: str, baseline: float, token: str):
    _test_text_generation(model_name, baseline, token, torch_compile=True)


@pytest.mark.parametrize("model_name, baseline", MODELS_TO_TEST["torch_compile_distributed"])
def test_text_generation_torch_compile_distributed(model_name: str, baseline: float, token: str):
    world_size = 8
    _test_text_generation(model_name, baseline, token, deepspeed=True, world_size=world_size, torch_compile=True)


@pytest.mark.parametrize("model_name, baseline", MODELS_TO_TEST["distributed_tp"])
def test_text_generation_distributed_tp(model_name: str, baseline: float, token: str):
    world_size = 8
    _test_text_generation(
        model_name,
        baseline,
        token,
        batch_size=64,
        max_input_tokens=128,
        world_size=world_size,
        torch_compile=True,
        parallel_strategy="tp",
    )


@pytest.mark.parametrize("model_name, batch_size, reuse_cache, baseline", MODELS_TO_TEST["contrastive_search"])
def test_text_generation_contrastive_search(
    model_name: str, baseline: float, batch_size: int, reuse_cache: bool, token: str
):
    _test_text_generation(model_name, baseline, token, batch_size, reuse_cache, contrastive_search=True)


class TextGenPipeline(TestCase):
    def test_text_generation_pipeline_script(self):
        path_to_script = (
            Path(os.path.dirname(__file__)).parent
            / "examples"
            / "text-generation"
            / "text-generation-pipeline"
            / "run_pipeline.py"
        )

        cmd_line = f"""ls {path_to_script}""".split()

        # check find existence
        p = subprocess.Popen(cmd_line)
        return_code = p.wait()

        # Ensure the run finished without any issue
        self.assertEqual(return_code, 0)

    def test_text_generation_pipeline_falcon(self):
        path_to_script = (
            Path(os.path.dirname(__file__)).parent
            / "examples"
            / "text-generation"
            / "text-generation-pipeline"
            / "run_pipeline.py"
        )
        sys.path.append((Path(os.path.dirname(__file__)).parent / "examples" / "text-generation"))
        cmd_line = f"""
                 python3
                 {path_to_script}
                 --model_name_or_path tiiuae/falcon-7b
                 --max_new_tokens 100
                 --bf16
                 --use_hpu_graphs
                 --use_kv_cache
                 --do_sample
                 """.split()
        p = subprocess.Popen(cmd_line)
        return_code = p.wait()

        # Ensure the run finished without any issue
        self.assertEqual(return_code, 0)
