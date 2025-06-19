
******************************************************* 
**Pre-requisite** 
******************************************************* 

1. QGPT code from - https://EnterpriseITTeam@dev.azure.com/EnterpriseITTeam/Enterprise%20IT-Initiatives/_git/qgpt_python
2. Anaconda 
3. Node (for windows) - for React UI
4. Ollama with require LLM models 
5. Python packages - refer requirement.txt file



******************************************************* 
**Installation & Deployment/Setup Steps for QGPT** 
******************************************************* 

Step 1. Building QGPT UI using React 
--------------------------------------------
-> Download the source code from ADO: https://EnterpriseITTeam@dev.azure.com/EnterpriseITTeam/Enterprise%20IT-Initiatives/_git/qgpt_python
-> Open cmd and go to React UI folder	cd C:\Everi\Application\qgpt_python
	cd qgpt_ui 
-> Run Npm install command 
	npm install --legacy-peer-deps
-> Run Npm build command 
	npm install react-icons  (if required)
	npm run build
-> Run Npm start command and verify the URL 
	npm run start
	Open URL: http://localhost:3000/
	
	
Step 2. Conda environment creation for QGPT
--------------------------------------------
-> Install Anaconda (latest version)
-> Run below commands
	conda deactivate
	conda env list	conda create --name qgpt_python python=3.11 
	#conda create -p "C:\Everi\Application\PythonEnv\qgpt_python" python=3.11

	conda activate qgpt_python


Step 3. Install Dependencies/ Packages for QGPT
--------------------------------------------
-> Run below command on conda QGPT environment 
	pip install -r requirements.txt 
	
-> Verify the installed packages 
	conda list > installed_packages.txt
 


Step 4. Install Ollama setup for QGPT
--------------------------------------------
-> Open cmd and go to QGPT folder
	cd C:\Everi\Application\qgpt_python
-> Run below command on conda QGPT environment 
	poetry install --extras "llms-ollama embeddings-ollama vector-stores-qdrant"
	#poetry install --extras "llms-ollama embeddings-ollama vector-stores-qdrant ui" -- in case of Gradio UI 

-> Known Issues: Copy the base.py file in the respective conda environment location 
	- copy base.py files to the below location : 
		<<conda environment>>\Lib\site-packages\llama_index\core\indices


-> Setting up the environment variables 
set OLLAMA_NUM_GPU=999
set no_proxy=localhost,127.0.0.1
set ZES_ENABLE_SYSMAN=1
set PGPT_PROFILES=ollama
set SYCL_CACHE_PERSISTENT=1
set OLLAMA_NO_INTERNET=true

-> Run below command for setting up PrivateGPT locally 
	poetry run python -m qgpt_core
	
-> Login QGPT, verify the functionality  
	URL: http://localhost:8001/


Step 5. Verify Resource monitoring for Ollama 
--------------------------------------------
-> Open cmd, run below command 
	ollama ps
	
	
***************************************************** 
End Step.
***************************************************** 

=======================================================================================

***************************************************** 
**QGPT Dashboard** 
*****************************************************
https://dev.azure.com/EnterpriseITTeam/Enterprise%20IT-Initiatives/_git/qgpt_python?path=/qgpt-dashboard.png&version=GBmain



***************************************************** 
**QGPT API Details** 
*****************************************************
https://dev.azure.com/EnterpriseITTeam/Enterprise%20IT-Initiatives/_git/qgpt_python?path=/qgpt-api-list.png&version=GBmain




Reference Command:
------------------

conda list > QGPT_installed_packages.txt

pip install --upgrade setuptools==75.8.0
pip install --upgrade virtualenv==20.26.6

conda env remove --name C:\Everi\Application\workspace\py_envs\qgpt
conda env remove --name qgpt

pip install -r requirements.txt

poetry install --extras "llms-ollama embeddings-ollama vector-stores-qdrant ui"

conda deactivate