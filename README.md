# steam-gift-bot
## Установка Google Chrome
```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
```
```bash
sudo dpkg -i google-chrome-stable_current_amd64.deb
```
Если возникла ошибка с зависимостями, автоматически их устанавливаем:
```bash
sudo apt install -f
```
## Репозиторий
```bash
git clone https://diprog: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@github.com/diprog/steam-gift-bot.git
```
## Python 3.11
```bash
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3-pip python3.11-venv -y
```
## Зависимости
```bash
pip install aiohttp aiofiles jsonpickle pytz python-dateutil lxml pyvirtualdisplay playwright 
```