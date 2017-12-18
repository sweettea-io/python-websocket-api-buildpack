FROM tiangolo/uwsgi-nginx-flask:python2.7

RUN pip install Flask==0.12.2 flask-restplus==0.10.1 boto3==1.4.7 pyyaml==3.12 SQLAlchemy==1.1.15 psycopg2==2.7.3

# Copy the current directory contents into the container at /app
COPY . /app

# upgrade pip and install required python packages (if requirements.txt is a thing)
RUN if [ -e /app/requirements.txt ]; then pip install -U pip && pip install -r /app/requirements.txt; fi