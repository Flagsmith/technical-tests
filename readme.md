# Flagsmith Technical Tests

Repository containing technical tests for applicants to work at Flagsmith. We currently have the following tests available:

1. [Server-side/Python/Django](/python-django/)
2. [Infrastructure/Kubernetes/DevOps](/kubernetes/) - Interactive debugging challenges for infrastructure roles

## Kubernetes Interview System

The `kubernetes/` directory contains a self-contained technical interview system for infrastructure and DevOps roles. It creates broken Flagsmith deployments that candidates must debug in real-time.

**Quick start:**
```bash
cd kubernetes/
make run
```

This launches an interactive system where you can select debugging challenges and share a terminal session with candidates. The system provides a complete Kubernetes environment with Flagsmith deployed in various broken states.

For detailed setup instructions, available challenges, and architecture information, see [kubernetes/README.md](kubernetes/README.md).

## Instructions

1. Clone this git repository which contains a number of individual tests in sub directories. You should only complete 
   the one relevant to the role you are applying for. This should be clear from your interactions with the flagsmith 
    hiring team, but please ask if not. 
2. Read the readme in the relevant test directory and answer the questions accordingly.  
3. Provide tests in your preferred style to support your solution. You can use common test libraries such as pytest.
4. Zip up and email the entire source tree to jobs@flagsmith.com. Please do not commit your answers to Github. 

**Note: Please do NOT spend more than 2 hours on this test.**

In addition to a working solution, we will be looking for:

 * Good coding style
 * Use of comments - especially if you get stuck on a question
 * Understanding of object orientation
 * Understanding of concurrency issues that might arise

**Note: Please do not push your test answers back onto Github.** 
