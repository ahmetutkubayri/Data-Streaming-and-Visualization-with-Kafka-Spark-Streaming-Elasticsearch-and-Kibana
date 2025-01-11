from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, FloatType, LongType
from elasticsearch import Elasticsearch

# Elasticsearch bağlantısı
try:
    es = Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])
    if not es.ping():
        raise Exception("Elasticsearch bağlantısı başarısız!")
    print("Elasticsearch bağlantısı başarılı.")
except Exception as e:
    print(f"Elasticsearch bağlanırken hata oluştu: {e}")
    exit(1)

# SparkSession başlat
spark = SparkSession.builder \
    .appName("Kafka Spark Streaming to Elasticsearch") \
    .master("local[*]") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.8") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoints") \
    .getOrCreate()

# Kafka'dan okunan verilerin şeması
schema = StructType([
    StructField("event_ts_min", StringType(), True),
    StructField("timestamp", LongType(), True),
    StructField("room", StringType(), True),
    StructField("co2", FloatType(), True),
    StructField("light", FloatType(), True),
    StructField("temp", FloatType(), True),
    StructField("humidity", FloatType(), True),
    StructField("pir", FloatType(), True),
])

# Kafka'dan veri oku
try:
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "office-input") \
        .option("startingOffsets", "earliest") \
        .load()
    print("Kafka'dan veri okuma başarılı.")
except Exception as e:
    print(f"Kafka bağlantısı sırasında hata oluştu: {e}")
    exit(1)

# JSON veriyi şemaya göre ayrıştır
parsed_df = kafka_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

# Elasticsearch'e veri yazan fonksiyon
def write_to_elasticsearch(partition):
    for row in partition:
        try:
            index_name = f"room-{row.room}"  # Oda ismine göre indeks oluştur
            document = row.asDict()  # Satırı dict formatına çevir
            es.index(index=index_name, body=document)
        except Exception as e:
            print(f"Elasticsearch'e veri yazılırken hata oluştu: {e}")

# Veriyi her mikropartisyonda Elasticsearch'e yaz
try:
    query = parsed_df.writeStream \
        .foreachBatch(lambda batch_df, batch_id: batch_df.foreachPartition(write_to_elasticsearch)) \
        .outputMode("append") \
        .start()
    print("Stream başlatıldı.")
    query.awaitTermination()
except Exception as e:
    print(f"Stream işlemi sırasında hata oluştu: {e}")
