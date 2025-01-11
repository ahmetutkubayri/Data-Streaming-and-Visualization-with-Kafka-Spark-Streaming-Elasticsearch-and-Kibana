# Kafka, Spark Streaming, Elasticsearch ve Kibana Projesi

Bu README dosyası, Kafka, Spark Streaming, Elasticsearch ve Kibana'yı kullanarak bir veri akışı oluşturma, işleme ve görselleştirme projesini adım adım açıklamaktadır. Her adım sürümler, kurulumlar ve kodlarla detaylandırılmıştır.

---

## Gerekli Araçlar ve Sürümler
Proje için aşağıdaki yazılımlar gereklidir:

1. **Docker ve Docker Compose**
   - Docker: `20.10.24`
   - Docker Compose: `2.20.0`
2. **Apache Kafka**
   - Kafka: `2.13-2.8.1`
3. **Apache Spark**
   - Spark: `2.4.8`
   - Spark SQL Kafka Connector: `2.4.8`
4. **Elasticsearch ve Kibana**
   - Elasticsearch: `7.17.9`
   - Kibana: `7.17.9`
5. **Python ve Kütüphaneler**
   - Python: `3.7`
   - Gerekli Kütüphaneler: `kafka-python`, `pyspark`, `elasticsearch`

---

## Projenin Yapısı

1. **Veri Hazırlığı**
   - Veri setini uygun bir formatta hazırlayıp Kafka’ya göndermek üzere kaydetmek.
2. **Kafka Kullanımı**
   - Kafka topic’leri oluşturmak ve veriyi Kafka’ya produce etmek.
3. **Spark Streaming**
   - Kafka’dan gelen veriyi tüketip yapılandırılmış hale getirerek Elasticsearch’e yazmak.
4. **Elasticsearch ve Kibana Kullanımı**
   - Verileri Elasticsearch’te saklayıp Kibana ile görselleştirmek.

---

## Adım 1: Veri Setini Hazırlama

Veri seti aşağıdaki gibi bir şemaya sahip olmalıdır:

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

1. **Adımlar:**
   - Bu formatta bir JSON dosyası veya CSV oluşturun.
   - Yerel diskte `data.json` veya `data.csv` adıyla saklayın.

---

## Adım 2: Kafka Kurulumu ve Veri Gönderimi

### 2.1 Docker ile Kafka ve Zookeeper’ı Çalıştırma
Aşağıdaki `docker-compose.yaml` dosyasını oluşturun:

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

### 2.2 Kafka Topic Oluşturma
Kafka’ya bağlanıp bir topic oluşturun:

```bash
docker exec -it kafka bash
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic office-input --partitions 3 --replication-factor 1
```

### 2.3 Kafka’ya Veri Gönderme
Python ile veri gönderimi için aşağıdaki script’i kullanın:

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
    print(f"Gönderildi: {record}")
    time.sleep(5)

producer.close()
```

---

## Adım 3: Spark Streaming ile Kafka’dan Veri Tüketimi

### 3.1 Spark Streaming Script’i
Spark Streaming ile Kafka’dan gelen veriyi işlemek için aşağıdaki script’i kullanın:

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, FloatType

spark = SparkSession.builder \
    .appName("Kafka Spark Streaming to Elasticsearch") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.8,org.elasticsearch:elasticsearch-spark-20_2.11:7.10.2") \
    .config("spark.es.nodes", "localhost") \
    .config("spark.es.port", "9200") \
    .getOrCreate()

schema = StructType([
    StructField("timestamp", StringType(), True),
    StructField("room", StringType(), True),
    StructField("co2", FloatType(), True),
    StructField("light", FloatType(), True),
    StructField("temp", FloatType(), True),
    StructField("humidity", FloatType(), True),
    StructField("pir", FloatType(), True)
])

kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "office-input") \
    .option("startingOffsets", "earliest") \
    .load()

json_df = kafka_df.selectExpr("CAST(value AS STRING) as json") \
    .select(from_json(col("json"), schema).alias("data")) \
    .select("data.*")

json_df.writeStream \
    .format("org.elasticsearch.spark.sql") \
    .option("es.resource", "office-index/_doc") \
    .outputMode("append") \
    .start() \
    .awaitTermination()
```

### 3.2 Spark Script’i Çalıştırma

```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.8,org.elasticsearch:elasticsearch-spark-20_2.11:7.10.2 --conf spark.es.nodes=localhost --conf spark.es.port=9200 --conf spark.es.nodes.wan.only=true --conf spark.es.index.auto.create=true spark_streaming_kafka.py 
```

---

## Adım 4: Kibana ile Görselleştirme

### 4.1 Elasticsearch ve Kibana’yı Çalıştırma
Docker kullanarak Elasticsearch ve Kibana’yı başlatın:

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

### 4.2 Kibana’da Index Pattern Oluşturma

1. Kibana’ya gidin: `http://localhost:5601`
2. **Stack Management** > **Index Patterns** > **Create Index Pattern** sekmesine gidin.
3. `office-index*` indexini seçip oluşturun.

### 4.3 Verileri Görselleştirme

1. **Discover** sekmesine giderek verileri kontrol edin.
2. **Visualize** sekmesinden yeni bir görselleştirme oluşturun:
   - Bar chart, line chart veya pie chart gibi seçenekler arasından birini seçin.

Kibana Ayarları ve Görselleştirme

Kibana'ya erişmek için tarayıcınızda http://localhost:5601 adresine gidin.

"Stack Management" sekmesine tıklayın ve "Index Patterns" oluşturun:

Örneğin: office-index.

Index pattern'ı oluştururken verilerinizi temsil eden bir zaman damgası alanını seçin.

"Discover" sekmesine giderek verilerinizi görüntüleyin.

"Visualize" sekmesinde aşağıdaki adımları izleyerek grafik oluşturabilirsiniz:

Yeni bir görselleştirme türü seçin (örneğin, bar chart).

X eksenine room, Y eksenine co2 gibi alanları ekleyerek görselleştirme yapın.

Grafiği kaydedin ve "Dashboard" sekmesinde bir pano oluşturarak ekleyin.

Sonuç

Bu rehber, veri akışını Kafka ile yönlendirme, Spark Streaming ile işleme, Elasticsearch ile depolama ve Kibana ile görselleştirme aşamalarını kapsamaktadır. Adımları takip ederek projeyi baştan sona başarıyla tamamlayabilirsiniz. Daha fazla bilgi için Elasticsearch, Apache Kafka, ve Apache Spark dokümantasyonlarını inceleyebilirsiniz.

