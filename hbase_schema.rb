# Final Project Part 1 — HBase table definitions.
# Run inside the final-hbase Docker container with: hbase shell hbase_schema.rb

['user_sessions', 'product_daily_metrics'].each do |table_name|
  if exists(table_name)
    disable(table_name)
    drop(table_name)
  end
end

# Rows are user_id|ISO-start-time|session_id, so all sessions for a user are
# contiguous and naturally ordered by time for prefix/range scans.
create 'user_sessions',
       { NAME => 'meta', VERSIONS => 1, BLOOMFILTER => 'ROW' },
       { NAME => 'device', VERSIONS => 1, BLOOMFILTER => 'ROW' },
       { NAME => 'geo', VERSIONS => 1, BLOOMFILTER => 'ROW' },
       { NAME => 'activity', VERSIONS => 1, BLOOMFILTER => 'ROW' }

# This table is designed for product-day performance queries. The assignment's
# simplified implementation loads the session table; later Spark work can
# compute and populate these product/day metrics.
create 'product_daily_metrics',
       { NAME => 'metrics', VERSIONS => 1, BLOOMFILTER => 'ROW' }

puts "\nCreated HBase tables:"
describe 'user_sessions'
describe 'product_daily_metrics'
exit
