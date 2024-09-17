# LLM Chat Web App with RAG and Chain of Thought capabilities

How to do it

*I am a mac user*

## Setup

This set up applies to all versions.

1. Create an AWS instance

EC2 instance

AMI: Ubuntu Server 22.04 LTS (HVM), SSD Volume Type

Instance Type: g4dn.xlarge
This instance type requires 4vcpu cores at the account level, which must be requested. Check this video for details on how do request these resources https://www.youtube.com/watch?v=jTgrK1_2JWs&t=56s

Create an ED25519 key pair with a .pem file format and save this file somewhere on your desktop

Create your own custom security group with the following rules
Inbound:
Type - Protocol - Port Range
SSH - TCP - 22
Custom TCP - TCP - 8080
HTTP - TCP -  80

Outbound:
Type - Protocol - Port Range
HTTP - TCP - 80
DNS(UDP) - UDP - 53
HTTPS - TCP - 443
DNS(TCP) - TCP - 53


Root Volume: 100 GiB

2. CLI setup

Open Terminal and SSH into your instance with the following command 
ssh -i /path/to/your/key.pem ubuntu@your-instance-public-dns
where your instance public dns is listed as "Public IPv4 Address" under your instance in the AWS console

If there is a permissions error in this step, you may need to run this command
chmod 400 /path/to/your/key.pem
then try to SSH in again

ssh -i /path/to/your/key.pem ubuntu@your-instance-public-dns

Then run the following commands to update the system and set up
If at any point you are presented with a colorful ubuntu screen, click enter when there is an 'ok' button. If there is a message about a reboot, press enter to proceed and it should select the correct boxes automatically.

sudo apt update && sudo apt upgrade -y

sudo apt install -y build-essential git wget curl python3 python3-pip python3-venv

sudo apt install -y docker.io 
sudo systemctl start docker 
sudo systemctl enable docker 
sudo usermod -aG docker $USER


Install Ollama

curl -O https://ollama.ai/install.sh

chmod +x install.sh 
sudo ./install.sh


Pull the Llama3.1-8b model

ollama pull llama3

Create a virtual environment

python3 -m venv ~/lenny_chat_env 
source ~/lenny_chat_env/bin/activate

pip install flask

(These two commands only needed for RAG version)
pip install PyPDF2 faiss-cpu sentence-transformers
pip freeze > requirements.txt

Create Lenny, our Llama model
ollama create lenny -f Modelfile_Lenny

(This model is needed for the CoT version)
ollama create lenny -f Modelfile_Lenny_cot

3. 
