 # Github Repository Research

**Week 3 of Summer Ladder Internship with SmartStickies**

## Repository Chosen

**GPT Engineer**  
GitHub: https://github.com/AntonOsika/gpt-engineer

---

# Overview

**GPT Engineer** could be a potential baseline for our AI Workflow Tool. GPT Engineer is an open-source Python project that uses Large Language Models (LLMs) to generate software projects from natural language prompts. Instead of manually creating files and writing code, users simply describe the application they want, and the AI generates the project structure and source code.

---

# Main Features

Some of the main features of GPT Engineer include:

* Generates software projects from natural language prompts
* Built entirely in Python
* Uses LLMs to plan and generate code
* Creates complete project structures instead of individual files
* Allows users to review and modify the generated output

---

# Why It Could Be a Good Baseline

I think GPT Engineer is a good starting point because it already demonstrates how an AI system can understand a user's requirements and generate something useful automatically.

It works somewhat like this:

User Prompt → LLM analyzes requirements → Generate project structure → Generate source code → User reviews the result

Create an application for a hospital that allows users to schedule and check appointment timesCreaat
This is similar to our project's goal. The main difference is that GPT Engineer generates source code, while our project would generate an application layout.

---

# What We Can Reuse In our Project

Some ideas from GPT Engineer that could be useful for our project include:

* Prompt-driven generation
* AI planning before generating the final output
* Modular project structure
* Python-based backend
* Ability to refine generated results

These ideas could help reduce the amount of manual work required when creating application layouts.

---

# What We Would Change

To better match the goals of our projects, I would make several changes.

### 1. Generate App Layouts Instead of Code

Currently, GPT Engineer produces project files and source code directly.

Instead, our system would generate an application layout first.

Example:

User Prompt → LLM analyzes requirements → Generate app layout → Display editable layout

This allows users to review the design before committing to implementation.

---

### 2. Add a Web-Based Interface

GPT Engineer is mainly operated through the command line.

For our project, I would replace the CLI with a web application where users can:

* Enter prompts
* View generated layouts
* Edit pages and components
* Save or export their work

This would make the tool more accessible, especially for users without programming experience.

---

### 3. Add Execution Metrics

Useful information such as:

* Token usage
* Response time
* Estimated API cost
* Selected LLM

could also be displayed after each generation. These metrics would help users compare models and monitor performance.

---

# Pros

* Open source
* Written in Python
* Easy to understand project structure
* Demonstrates prompt-based AI generation
* Can be extended for different AI tasks

# Cons

* No graphical user interface
* Focuses on generating code instead of layouts
* Requires programming knowledge to use effectively
* No visual editing of generated results

---

# Conclusion

To adapt GPT Engineer for our AI Workflow Tool, I would replace code generation with application layout generation and build a web-based interface that allows users to view and edit the generated layout. This would make the system more interactive and better help quickly design layouts
