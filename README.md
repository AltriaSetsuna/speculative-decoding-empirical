*   **Model Deployment:** Please install the vLLM inference framework first. By default, please install version 0.12.0. After the framework is installed, navigate to the `vllm/scripts` folder and run the corresponding commands to complete the model deployment.
    
*   **Dataset and Environment Configuration:** For the three datasets used in this evaluation, please refer to the official links below for basic environment configuration. To ensure the experiments run correctly, please use the code provided in this repository, which includes the necessary modifications for this study. Please do not clone the official repositories directly. After the environment configuration is complete, you can directly run the corresponding bash script files for each dataset.
    
    *   LiveCodeBench: The reference link is [https://github.com/LiveCodeBench/LiveCodeBench](https://github.com/LiveCodeBench/LiveCodeBench). The execution files are located in the `LiveCodebench/scripts` directory.
        
    *   SWE-bench: This part of the experiment uses the mini-swe-agent framework for evaluation. The reference link is [https://github.com/SWE-agent/mini-swe-agent/tree/main](https://github.com/SWE-agent/mini-swe-agent/tree/main). The execution files are located in the `mini-swe-agent/scripts` directory.
        
    *   Aider Polyglot: The reference link is [https://github.com/Aider-AI/aider/tree/v0.86.1/benchmark](https://github.com/Aider-AI/aider/tree/v0.86.1/benchmark). The execution files are located in the `aider/spec_scripts` directory.
