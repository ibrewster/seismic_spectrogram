FROM ubuntu:latest
# SET SOME ENVIROMENT VARIABLES FOR THE CONFIG PROCESS
# MODIFY THESE AS NEEDED TO MATCH YOUR INSTALLATION
ENV MySQL__DB_USER <myuser>
ENV MySQL__DB_PASSWORD <mypassword>
# END USER ENVIROMENT
ENV DEBIAN_FRONTEND noninteractive
WORKDIR /code
RUN apt-get update && apt-get -y upgrade && apt-get -y install git cron nano python3 python3-pip libgdal-dev fftw3-dev r-base
RUN git clone https://github.com/ibrewster/seismic_spectrogram.git .
RUN Rscript docker/install_r_packages.R
RUN pip3 install uwsgi
ADD http://worldtimeapi.org/api/ip.txt /tmp/bustcache
RUN git pull
RUN python3 setup.py -y
RUN mkdir /var/log/specweb && chmod 777 /var/log/specweb
RUN mkdir /var/run/specweb && chmod 777 /var/run/specweb
COPY docker/generate-cron /etc/cron.d/generate-cron
RUN chmod 0644 /etc/cron.d/generate-cron
RUN crontab /etc/cron.d/generate-cron
RUN touch /var/log/cron.log
CMD cron && uwsgi -i ./specweb/specweb.ini