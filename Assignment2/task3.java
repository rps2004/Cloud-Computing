package org.myorg.taxi;

import java.io.IOException;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.Map.Entry;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.*;
import org.apache.hadoop.mapreduce.*;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

public class TopLocations2012MostVisited {

    // Mapper: emit (location, 1) for 2012 pickups and dropoffs
    public static class LocationCountMapper extends Mapper<LongWritable, Text, Text, IntWritable> {
        private final static IntWritable ONE = new IntWritable(1);
        private Text locKey = new Text();
        private Pattern datePattern = Pattern.compile("(\\d{4})-(\\d{2})-(\\d{2})");

        @Override
        protected void map(LongWritable key, Text value, Context context) throws IOException, InterruptedException {
            String line = value.toString();
            if (line == null || line.trim().isEmpty()) return;

            String low = line.toLowerCase();
            if (low.contains("pickup_datetime") && low.contains("pickup_longitude")) return;

            String[] tokens = line.split(",");
            if (tokens.length < 7) return;

            String pickupDatetime = tokens[2].trim();
            String pickupLon = tokens[3].trim();
            String pickupLat = tokens[4].trim();
            String dropLon = tokens[5].trim();
            String dropLat = tokens[6].trim();

            Matcher m = datePattern.matcher(pickupDatetime);
            if (!m.find()) return;
            String year = m.group(1);
            if (!"2012".equals(year)) return;

            // Emit pickup location
            locKey.set(pickupLon + "," + pickupLat);
            context.write(locKey, ONE);

            // Emit drop location
            locKey.set(dropLon + "," + dropLat);
            context.write(locKey, ONE);
        }
    }

    // Reducer: sum counts per location and keep top 5
    public static class Top5LocationReducer extends Reducer<Text, IntWritable, Text, IntWritable> {
        private PriorityQueue<Entry<String, Integer>> pq = new PriorityQueue<>(5,
            Comparator.comparingInt(Entry::getValue));

        @Override
        protected void reduce(Text key, Iterable<IntWritable> values, Context context)
                throws IOException, InterruptedException {
            int sum = 0;
            for (IntWritable v : values) sum += v.get();
            pq.add(new AbstractMap.SimpleEntry<>(key.toString(), sum));
            if (pq.size() > 5) pq.poll();
        }

        @Override
        protected void cleanup(Context context) throws IOException, InterruptedException {
            List<Entry<String, Integer>> topList = new ArrayList<>();
            while (!pq.isEmpty()) topList.add(pq.poll());
            Collections.reverse(topList);
            for (Entry<String, Integer> e : topList) {
                context.write(new Text(e.getKey()), new IntWritable(e.getValue()));
            }
        }
    }

    // Driver
    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("Usage: TopLocations2012MostVisited <inputCsv> <finalOutput>");
            System.exit(2);
        }

        String input = args[0];
        String finalOut = args[1];
        Configuration conf = new Configuration();

        Job job = Job.getInstance(conf, "Top 5 Most Visited Locations 2012 - Single Job");
        job.setJarByClass(TopLocations2012MostVisited.class);

        job.setMapperClass(LocationCountMapper.class);
        job.setReducerClass(Top5LocationReducer.class);

        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(IntWritable.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(IntWritable.class);

        FileInputFormat.setInputPaths(job, new Path(input));
        FileOutputFormat.setOutputPath(job, new Path(finalOut));

        job.setNumReduceTasks(1);

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}