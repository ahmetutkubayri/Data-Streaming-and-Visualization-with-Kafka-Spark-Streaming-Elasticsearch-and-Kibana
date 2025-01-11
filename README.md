# Kafka, Spark Streaming, Elasticsearch, and Kibana Project

This README file explains step by step how to create, process, and visualize a data stream using Kafka, Spark Streaming, Elasticsearch, and Kibana. Each step is detailed with versions, installations, and code.

---

## Required Tools and Versions
The following software is required for the project:

1. **Docker and Docker Compose**
   - Docker: `20.10.24`
   - Docker Compose: `2.20.0`
2. **Apache Kafka**
   - Kafka: `2.13-2.8.1`
3. **Apache Spark**
   - Spark: `2.4.8`
   - Spark SQL Kafka Connector: `2.4.8`
4. **Elasticsearch and Kibana**
   - Elasticsearch: `7.17.9`
   - Kibana: `7.17.9`
5. **Python and Libraries**
   - Python: `3.7`
   - Required Libraries: `kafka-python`, `pyspark`, `elasticsearch`

---

## Project Structure

1. **Data Preparation**
   - Preparing the dataset in an appropriate format to send to Kafka.
2. **Kafka Usage**
   - Creating Kafka topics and producing data to Kafka.
3. **Spark Streaming**
   - Consuming data from Kafka, structuring it, and writing it to Elasticsearch.
4. **Elasticsearch and Kibana Usage**
   - Storing data in Elasticsearch and visualizing it with Kibana.

---

## Step 1: Preparing the Dataset

The dataset should have the following schema:

```json
{
  "timestamp": "2025-01-03T12:00:00",
  "room": "413",
  "co2": 500.0,
  "light": 300.0,
  "temp": 22.5,
  "humidity": 45.0,
  "pir": 1.0
}
```

1. **Steps:**
   - Create a JSON or CSV file in this format.
   - Save it locally as `data.json` or `data.csv`.

---

## Step 2: Setting Up Kafka and Sending Data

### 2.1 Running Kafka and Zookeeper with Docker
Create the following `docker-compose.yaml` file:

```yaml
version: '3.7'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    container_name: zookeeper
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:latest
    container_name: kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

### 2.2 Creating a Kafka Topic
Connect to Kafka and create a topic:

```bash
docker exec -it kafka bash
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic office-input --partitions 3 --replication-factor 1
```

### 2.3 Sending Data to Kafka
Use the following Python script to send data to Kafka:

```python
from kafka import KafkaProducer
import json
import time

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

data = [
    {"timestamp": "2025-01-03T12:00:00", "room": "413", "co2": 500.0},
    {"timestamp": "2025-01-03T12:00:10", "room": "415", "co2": 505.0},
    {"timestamp": "2025-01-03T12:00:20", "room": "417", "co2": 495.0}
]

for record in data:
    producer.send('office-input', value=record)
    print(f"Sent: {record}")
    time.sleep(5)

producer.close()
```

---

## Step 3: Consuming Data from Kafka with Spark Streaming

### 3.1 Spark Streaming Script
Use the following script to process data from Kafka and send it to Elasticsearch:

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, FloatType

spark = SparkSession.builder     .appName("Kafka Spark Streaming to Elasticsearch")     .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.8,org.elasticsearch:elasticsearch-spark-20_2.11:7.10.2")     .config("spark.es.nodes", "localhost")     .config("spark.es.port", "9200")     .getOrCreate()

schema = StructType([
    StructField("timestamp", StringType(), True),
    StructField("room", StringType(), True),
    StructField("co2", FloatType(), True),
    StructField("light", FloatType(), True),
    StructField("temp", FloatType(), True),
    StructField("humidity", FloatType(), True),
    StructField("pir", FloatType(), True)
])

kafka_df = spark.readStream     .format("kafka")     .option("kafka.bootstrap.servers", "localhost:9092")     .option("subscribe", "office-input")     .option("startingOffsets", "earliest")     .load()

json_df = kafka_df.selectExpr("CAST(value AS STRING) as json")     .select(from_json(col("json"), schema).alias("data"))     .select("data.*")

json_df.writeStream     .format("org.elasticsearch.spark.sql")     .option("es.resource", "office-index/_doc")     .outputMode("append")     .start()     .awaitTermination()
```

### 3.2 Running the Spark Script

```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.8,org.elasticsearch:elasticsearch-spark-20_2.11:7.10.2 spark_streaming_kafka.py
```

---

## Step 4: Visualizing with Kibana

### 4.1 Running Elasticsearch and Kibana
Start Elasticsearch and Kibana with the following `docker-compose.yaml`:

```yaml
version: '3.7'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.17.9
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:7.17.9
    container_name: kibana
    ports:
      - "5601:5601"
```

### 4.2 Creating an Index Pattern in Kibana

1. Go to Kibana: `http://localhost:5601`
2. Navigate to **Stack Management** > **Index Patterns** and create an index pattern.
3. Select `office-index*` and finish the setup.

### 4.3 Visualizing Data
1. Check data in the **Discover** tab.
2. Create a new visualization (e.g., bar chart, line chart) under the **Visualize** tab.


