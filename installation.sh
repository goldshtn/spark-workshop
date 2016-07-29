# oracle java 8
echo "\n" | sudo add-apt-repository ppa:openjdk-r/ppa
sudo apt-get update -y
sudo apt-get install -y openjdk-8-jdk

# spark download and setup
wget https://d3kbcqa49mib13.cloudfront.net/spark-1.6.1-bin-hadoop2.6.tgz -O /tmp/spark-1.6.1.tgz
sudo ufw disable
sudo mkdir -p /usr/lib/spark
sudo tar -xf /tmp/spark-1.6.1.tgz --strip 1 -C /usr/lib/spark
echo "export JAVA_HOME=/usr/lib/jvm/java-8-oracle" >> ~/.bash_profile
echo "export PATH=\$JAVA_HOME/bin:\$PATH" >> ~/.bash_profile
echo "export SPARK_HOME=/usr/lib/spark" >> ~/.bash_profile
echo "export PATH=\$SPARK_HOME/bin:\$PATH" >> ~/.bash_profile
source ~/.bash_profile

# spark log config
sudo rm /usr/lib/spark/conf/log4j.properties
sudo touch /usr/lib/spark/conf/log4j.properties
sudo bash -c 'cat << EOF > /usr/lib/spark/conf/log4j.properties
# Set everything to be logged to the console
log4j.rootCategory=WARN, console
log4j.appender.console=org.apache.log4j.ConsoleAppender
log4j.appender.console.target=System.err
log4j.appender.console.layout=org.apache.log4j.PatternLayout
log4j.appender.console.layout.ConversionPattern=%d{yy/MM/dd HH:mm:ss} %p %c{1}: %m%n

# Settings to quiet third party logs that are too verbose
log4j.logger.org.spark-project.jetty=WARN
log4j.logger.org.spark-project.jetty.util.component.AbstractLifeCycle=ERROR
log4j.logger.org.apache.spark.repl.SparkIMain$exprTyper=WARN
log4j.logger.org.apache.spark.repl.SparkILoop$SparkILoopInterpreter=WARN
log4j.logger.org.apache.parquet=ERROR
log4j.logger.parquet=ERROR

# SPARK-9183: Settings to avoid annoying messages when looking up nonexistent UDFs in SparkSQL with Hive support
log4j.logger.org.apache.hadoop.hive.metastore.RetryingHMSHandler=FATAL
log4j.logger.org.apache.hadoop.hive.ql.exec.FunctionRegistry=ERROR
EOF'

# spark default config
sudo rm /usr/lib/spark/conf/spark-defaults.conf
sudo touch /usr/lib/spark/conf/spark-defaults.conf
sudo bash -c 'cat << EOF > /usr/lib/spark/conf/spark-defaults.conf
spark.master                     spark://$(hostname):7077
spark.eventLog.enabled           true
spark.eventLog.dir               file:///usr/lib/spark/logs/eventlog
EOF'
sudo mkdir -p /usr/lib/spark/logs/eventlog
sudo chmod -R 777 /usr/lib/spark/logs

# zeppelin setup
ZEPPLIN_URL=$(curl http://www.apache.org/dyn/closer.cgi/zeppelin/zeppelin-0.6.0/zeppelin-0.6.0-bin-all.tgz  |   grep -o '<strong>[^<]*</strong>' |   sed 's/<[^>]*>//g' | head -1)
wget $ZEPPLIN_URL -O /tmp/zeppelin-0.6.0.tgz
sudo mkdir -p /usr/lib/zeppelin
sudo tar -xf /tmp/zeppelin-0.6.0.tgz --strip 1 -C /usr/lib/zeppelin

# zeppelin config
sudo rm /usr/lib/zeppelin/conf/zeppelin-env.sh
sudo touch /usr/lib/zeppelin/conf/zeppelin-env.sh
sudo bash -c 'cat << EOF > /usr/lib/zeppelin/conf/zeppelin-env.sh
#!/bin/bash
export JAVA_HOME=/usr/lib/jvm/java-8-oracle
export MASTER=spark://$(hostname):7077
export SPARK_HOME=/usr/lib/spark
export ZEPPELIN_PORT=9995
# export SPARK_SUBMIT_OPTIONS
EOF'

sudo ufw disable

# start everything up
sudo /usr/lib/spark/sbin/stop-master.sh
sudo /usr/lib/spark/sbin/stop-slave.sh
sudo /usr/lib/spark/sbin/start-master.sh
sudo bash -c '/usr/lib/spark/sbin/start-slave.sh spark://$(hostname):7077'
sudo /usr/lib/zeppelin/bin/zeppelin-daemon.sh restart
