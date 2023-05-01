
# pull official base image
FROM corilo/corems:base-mono-pythonnet

# set work directory
WORKDIR /usr/src/corems_uploader

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/corems_uploader/requirements.txt
RUN pip install -U -r requirements.txt

# copy project
COPY . /usr/src/corems_uploader
# CMD ["gunicorn", "-w", "2","-t", "1200","--threads", "4","--worker-tmp-dir", " /dev/shm", "-b", ":3443", "api:create_app()"]

# windows deployment 
CMD ["waitress-serve", "--listen=*:8000", "--call", "api:create_app"]
