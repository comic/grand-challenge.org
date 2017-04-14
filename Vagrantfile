# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"
  config.vm.network "forwarded_port", guest: 8000, host: 8000

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "2048"
  end

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update && apt-get upgrade -y

    apt-get install -y python python-pip python-openssl libpng-dev libjpeg-dev libjpeg8-dev libfreetype6-dev libxft-dev libmysqlclient-dev libffi-dev mariadb-server

    cp /vagrant/testing/60-mariadb.cnf /etc/mysql/mariadb.conf.d/
    service mysql restart
    mysql -u root --password= -e "CREATE DATABASE comic DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;"

    pip install --upgrade pip
    pip install -r /vagrant/requirements.txt

  SHELL
end
