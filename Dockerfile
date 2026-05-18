FROM python:3.12

WORKDIR /tgbot

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# ports, likely will edit
EXPOSE 3000

CMD ["python3", "bot.py"]