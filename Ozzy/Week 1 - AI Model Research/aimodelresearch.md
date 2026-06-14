# AI Model Research — Ozzy
**Week 1 of Summer Ladder Internship with SmartStickies**


### Task Overview
* Research at least 3 different FREE LLMS over the net, what’s the pros/cons, costs of using these models
* Try running/ calling these models, create simple UI text input, and see LLMs response. 


> The models that I chose to research are lightweight, compact, and optimized for resource-constrained environments.

The cost of running the models on various API providers can be found [here](pricing.md)  
To see some example inputs and outputs for the various models see [here](testing.md)  
To test some inputs to the models yourself this [this executable](exec/testall.exe)  
The code for the executable is [here](exec/testall.py)


### Contents
* [1. `openai/gpt-oss-20b`](#1-openai-gpt-oss-20b)
    * [Licensing & Compliance](#licensing--compliance)
    * [Pros & Cons](#pros--cons)
    * [Why use `gpt-oss-20b` over `gpt-oss-120b`?](#why-use-gpt-oss-20b-over-gpt-oss-120b)
* [2. `microsoft/Phi-4-mini-instruct`](#2-microsoftphi-4-mini-instruct)
    * [Licensing & Compliance](#licensing--compliance-1)
    * [Pros & Cons](#pros--cons-1)
    * [The Phi-4 Family](#the-phi-4-family)
* [3. `meta-llama/Llama-3.1-8B`](#3-meta-llamallama-31-8b)
    * [Licensing & Compliance](#licensing--compliance-2)
    * [Pros & Cons](#pros--cons-2)
    * [The Llama 3.1 Family](#the-llama-31-family)
* [Other Thoughts](#other-thoughts)

---

## 1. `openai/gpt-oss-20b`

> **Hugging Face:** [`openai/gpt-oss-20b`](https://huggingface.co/openai/gpt-oss-20b)  
  **GitHub:** [`openai/gpt-oss`](https://github.com/openai/gpt-oss)  
  **Docs:** [`gpt-oss-20b`](https://developers.openai.com/api/docs/models/gpt-oss-20b)

OpenAI's **`gpt-oss-20b`** is a fast and resource-efficient reasoning engine. It belongs to the `gpt-oss` collection and has a larger sibling in the `gpt-oss-120b`.

### Licensing & Compliance
The model is distributed under the **Apache 2.0** license. 

**Requirements for Use:**
* Include a copy of the license.
* Retain copyright notices from the original open-oss repository.
* Explicitly state any changes made to the source.
* Include the original repository's `NOTICE` file.

**Permissions:**
* Modify the source code freely.
* Deploy it internally or package it within a commercial software product.

### Pros & Cons

| Pros | Cons |
| :--- | :--- |
| **Low Resource Hardware:** Can run locally with just 16 GB of memory. | **Text-Only:** Lacks vision capabilities and is purely text-in, text-out. |
| **Configurable Reasoning:** Effort can be set to low, medium, or high to optimize performance based on needs. | **Domain/Language Constraints:** Training data explicitly targets English, STEM, and coding. It may struggle with multilingual inputs. |
| **Template Replication:** Reliably mirrors template formats, allowing explicit control over structured outputs. | **Performance Ceiling:** Struggles with complex tasks that may instead require the `gpt-oss-120b`. |
| **Generous Context:** Supports up to a 128k token context length for handling large datasets. | |
| **Adaptability:** Highly fine-tunable for specialized enterprise use cases. | |

### Why use `gpt-oss-20b` over `gpt-oss-120b`?
* `gpt-oss-120b` has a significantly slower generation speed.
* Running `gpt-oss-120b` demands enterprise-grade hardware, whereas `gpt-oss-20b` runs on relatively low-cost local computing setups.
* Handling layout formulation is a relatively simple task that `gpt-oss-20b` can easily accomplish without the massive computational overhead of the 120B variant.

---

## 2. `microsoft/Phi-4-mini-instruct`

>  **Hugging Face:** [`microsoft/Phi-4-mini-instruct`](https://huggingface.co/microsoft/Phi-4-mini-instruct)  
  **GitHub:** [`PhiCookBook`](https://github.com/microsoft/PhiCookBook)  
  **Docs:** [`Phi-4-mini-instruct`](https://ai.azure.com/catalog/models/Phi-4-mini-instruct)

Microsoft's **`Phi-4-mini-instruct`** is the smallest model in the Phi-4 family, engineered specifically for high efficiency in memory-constrained setups.

### Licensing & Compliance
Distributed under the highly permissive **MIT License**.
**Requirements for use:** 
* Must include Microsoft's original copyright notice and the MIT permission notice.

**Permissions:** 
* Free commercial deployment 
* Fine-tuning without the need to open-source the modifications.

### Pros & Cons

| Pros | Cons |
| :--- | :--- |
| **Minimal Footprint:** Requires very little memory—only 4 GB to 6 GB when optimized. | **Text-Only:** Limited strictly to text inputs and outputs; cannot process visual components. |
| **Permissive Licensing:** MIT License eliminates the need to track code modifications. | **Complex Data Structures:** Gets confused by complex layouts, such as generating nested lists. |
| **Hyper-Fast Output:** Generates 115–200 tokens/sec, eliminating the typical 1–3 second lag seen in larger models. | **No Pre-reflection:** Lacks internal planning steps, meaning it can run out of structural "space" mid-generation. |
| **Large Context Window:** 128k context length allows for massive input processing. | **Constraint Sensitivity:** Tends to drop rules or overlook conditions if a prompt is overly restrictive or complex. |
| **Native Tooling:** Microsoft trained it natively to support function calling and structured JSON formats. | |

### The Phi-4 Family
The Phi-4 ecosystem is divided into three primary categories:

* **`Phi-4` (Standard):** Includes `Phi-4`, `Phi-4-Reasoning`, and `Phi-4-Reasoning-Plus`. These are flagship, STEM-optimized models tailored for data centers or high-end workstations. The reasoning variants offer deep precision but introduce significant latency.
* **`Phi-4-Mini`:** Includes `Phi-4-mini-instruct` and `Phi-4-mini-reasoning`. Designed for edge and consumer devices to allow wide-scale deployment. The instruct variant circumvents the high latency of the reasoning variants while preserving a tiny memory footprint.
* **`Phi-4-Multimodal`:** Includes `Phi-4-multimodal-instruct` and `Phi-4-reasoning-vision-15B`. Built with audio and vision encoders. The 15B variant sits on the core Phi-4 architecture to tackle high-end, multi-sensory tasks.

The `Phi-4-mini-instruct` stands out as the optimal choice out of the `Phi-4` family for standard workflow automation due to its rapid execution speeds, tiny resource footprint, and lack of latency bottlenecks.

---

## 3. `meta-llama/Llama-3.1-8B`

> **Hugging Face:** [`meta-llama/Llama-3.1-8B`](https://huggingface.co/meta-llama/Llama-3.1-8B)  
  **GitHub:** [`llama3`](https://github.com/meta-llama/llama3)  
  **Docs:** [`Llama 3.1`](https://www.llama.com/docs/model-cards-and-prompt-formats/llama3_1/)

Meta's **`Llama-3.1-8B`** is an upgraded version of the older Llama-3-8B. It represents the smallest tier in a family that scales up to 70B and 405B parameter models.

### Licensing & Compliance
Distributed under the **Llama 3.1 Community License**.

**Requirements for use:**
* Distribute a copy of the license agreement and have a `Notice` file containing the following:  
  **"Llama 3.1 is licensed under the Llama 3.1 Community License, Copyright © Meta Platforms, Inc. All Rights Reserved."**
* If commercially distributed, the product must display **"Built with Llama"** on it
* If a model was trained using Llama 3.1 data or weights, it must include **"Llama** at the beginning of the model name
* If the product or services exceeds 700 million Monthly Active Users, a separate enterprise license must be requested from Meta
* The model cannot be distributed to the following:  
  * Unlicensed professional services (legal counsel, auditing, medical analysis)
  * High-Risk infrastructure and machinery (public transit, nuclear infrastructure) 
  * For the use of harm (generating malware, weapon development, espionage)

**Permissions:**
* Integrate the model into revenue generating products (use it commercially)
* Freely modify the parameters and fine-tune the model weights
* No requirement to open-source modifications
* Use the model to train other model


### Pros & Cons

| Pros | Cons |
| :--- | :--- |
| **Edge-Friendly:** Low memory demands (4B–8B footprint) allow deployment on dense consumer devices. | **Analytical Ceilings:** Exceptional at synthesis and classification, but struggles with deep algorithmic/math logic due to its 8B scale. |
| **Expanded Context:** Upgraded from the original 8k ceiling to a massive 128k token context window. | **No Native Multimodal:** Purely text-based; incapable of reading screenshots or graphics. |
| **Structured Output Reliability:** Rarely hallucinates arguments or outputs conversational filler when forced into direct code/JSON array generation. | **Moderate Speed:** Highly efficient, but cannot fully match the hyper-fast token production speeds of ultra-lightweight models. |
| **Massive Ecosystem:** A large community that uses it means predictable fine-tuning and compatibility with nearly every local inference tool. | |

### The Llama 3.1 Family
The Llama 3.1 family has three sizing classes to fit various hardware budgets and operational scopes:

`Llama-3.1-8B` was built for local workstations and low-latency edge environments. It is popular for local background daemons, text classification, and schema clamping. Its 4-bit or 8-bit footprint runs silently alongside standard desktop developer tools.

`Llama-3.1-70B` demands multi-GPU setups or high-capacity memory environments but delivers significantly deeper analytical reasoning. It excels at processing complex business logic, parsing heavy database logs, and automating enterprise tasks.

`Llama-3.1-405B` is the crown jewel of the 3.1 family. It has a massive footprint and is primarily hosted on data-center clusters and utilized for high-order logic, complex mathematical proofs, and generating synthetic data to train smaller edge models.

---

## Other Thoughts

1. Instead of running the AI models through an API, if run locally through managers such as Ollama, we can avoid API costs. It just depends on if our equipment has the capabilities.


2. If we want to build a dynamic UI that adapts to user preferences over time, we could try to implement something like this:

```mermaid
graph TD
    A[1. User interacts with program] --> B
    B[2. Data of user's behavior is collected] --> C
    C[3. Using ML classification, what user wants to do is identified] --> D
    D[4. Using a LLM, the user's intent is translated into a JSON] --> E
    E[5. The UI rearranges based on the JSON]