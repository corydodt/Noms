# vim:set ft=dockerfile:
FROM corydodt/circus-base:0.3-ubuntu

ENV noms /opt/Noms

WORKDIR $noms

COPY ./package.json ./requirements.txt /

RUN pip install httpie

# Ubuntu's node is too old so we prepare to install a newer version
RUN apt -y update \
  && apt -y install apt-transport-https \
  && http get https://deb.nodesource.com/gpgkey/nodesource.gpg.key | \
    apt-key add - \
  && echo "deb https://deb.nodesource.com/node_9.x xenial main" | \
    tee /etc/apt/sources.list.d/nodesource.list \
  && echo "deb-src https://deb.nodesource.com/node_9.x xenial main" | \
    tee -a /etc/apt/sources.list.d/nodesource.list \
  && apt clean \
  && apt autoclean

# Ubuntu's mongodb is also too old, prepare to install newer
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2930ADAE8CAF5059EE73BB4B58712A2291FA4AD5 \
    && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.6 multiverse" | \
      tee /etc/apt/sources.list.d/mongodb-org-3.6.list

# install deb (OS) packages - required files at runtime
RUN apt -y update \
    && apt -y install \
       git \
       mongodb-org-shell \
       mongodb-org-tools \
       netcat \
       nodejs \
       python-pip \
       rlwrap \
       vim \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* \
    && apt clean \
    && apt autoclean

# install dev-only packages in a separate layer while we install pip software
RUN apt update && apt -y install \
       libffi-dev \
       libssl-dev \
       python-dev \
    && mv /package.json $noms \
    && npm install \
    && mv node_modules / \
    && pip install -U pip \
    && /usr/local/bin/pip --no-cache-dir install -r /requirements.txt \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* \
    && apt -y remove \
       libffi-dev \
       libssl-dev \
       python-dev \
    && apt clean \
    && apt autoclean

# shell environment
ENV PATH $PATH:$noms/bin:$noms/node_modules/.bin:/node_modules/.bin
ENV PYTHONPATH=$noms
ENV NODE_PATH=/node_modules

COPY ./00-noms.ini /etc/circus.d/

EXPOSE 8080

# install all source
COPY . .

RUN node-sass static/scss/base.scss -o static/css
