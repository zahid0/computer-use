FROM python

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

COPY . /app
CMD uvicorn main:app --host 0.0.0.0 --env-file .env --reload
