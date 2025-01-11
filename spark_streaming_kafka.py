from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, FloatType

# Spark oturumunu başlat
spark = SparkSession.builder \
    .appName("Kafka-Spark-Streaming") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoints") \
    .config("spark.sql.debug.maxToStringFields", "200") \
    .getOrCreate()

# Kafka'dan veri oku
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "office-input") \
    .option("startingOffsets", "earliest") \
    .load()

# Mesajları JSON formatına ayrıştırmak için schema tanımla
schema = StructType([
    StructField("timestamp", StringType(), True),
    StructField("room", StringType(), True),
    StructField("co2", FloatType(), True),
    StructField("light", FloatType(), True),
    StructField("temp", FloatType(), True),
    StructField("humidity", FloatType(), True),
    StructField("pir", FloatType(), True)
])

# Kafka mesajlarını JSON formatına dönüştür ve ayrıştır
json_df = kafka_df.selectExpr("CAST(value AS STRING) as json") \
    .select(from_json(col("json"), schema).alias("data")) \
    .select("data.*")

# Elasticsearch'e yazma
json_df.writeStream \
    .format("org.elasticsearch.spark.sql") \
    .option("es.nodes", "localhost:9200") \
    .option("es.resource", "office-index/_doc") \
    .option("es.mapping.id", "room") \
    .outputMode("append") \
    .start() \
    .awaitTermination()
