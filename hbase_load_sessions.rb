# Final Project Part 1 — load a representative 10,000-session subset.
# The prepared subset avoids exhausting the limited Java heap of the HBase shell.

require 'json'
java_import org.apache.hadoop.hbase.client.Put

INPUT_FILE = '/tmp/sessions_subset_10000.json'
MAX_SESSIONS = 10_000

sessions = JSON.parse(File.read(INPUT_FILE)).first(MAX_SESSIONS)
# Use the underlying Java table API for true multi-column batch puts. The HBase
# shell's table.put shortcut only accepts one column and one value at a time.
hbase_table = get_table('user_sessions').table
write_batch = java.util.ArrayList.new

def bytes(value)
  value.to_s.to_java_bytes
end

puts "Loading #{sessions.length} sessions into user_sessions ..."

sessions.each_with_index do |session, index|
  # ISO timestamps sort chronologically, and the session id ensures row-key uniqueness.
  row_key = "#{session['user_id']}|#{session['start_time']}|#{session['session_id']}"
  cart = session['cart_contents'] || {}
  page_views = session['page_views'] || []
  device = session['device_profile'] || {}
  geo = session['geo_data'] || {}

  put = Put.new(bytes(row_key))
  put.addColumn(bytes('meta'), bytes('session_id'), bytes(session['session_id']))
  put.addColumn(bytes('meta'), bytes('start_time'), bytes(session['start_time']))
  put.addColumn(bytes('meta'), bytes('end_time'), bytes(session['end_time']))
  put.addColumn(bytes('meta'), bytes('duration_seconds'), bytes(session['duration_seconds']))
  put.addColumn(bytes('meta'), bytes('conversion_status'), bytes(session['conversion_status']))
  put.addColumn(bytes('meta'), bytes('referrer'), bytes(session['referrer']))
  put.addColumn(bytes('device'), bytes('type'), bytes(device['type']))
  put.addColumn(bytes('device'), bytes('os'), bytes(device['os']))
  put.addColumn(bytes('device'), bytes('browser'), bytes(device['browser']))
  put.addColumn(bytes('geo'), bytes('city'), bytes(geo['city']))
  put.addColumn(bytes('geo'), bytes('state'), bytes(geo['state']))
  put.addColumn(bytes('geo'), bytes('country'), bytes(geo['country']))
  put.addColumn(bytes('geo'), bytes('ip_address'), bytes(geo['ip_address']))
  put.addColumn(bytes('activity'), bytes('viewed_products_json'), bytes(JSON.generate(session['viewed_products'] || [])))
  put.addColumn(bytes('activity'), bytes('page_view_count'), bytes(page_views.length))
  put.addColumn(bytes('activity'), bytes('cart_item_count'), bytes(cart.length))
  put.addColumn(bytes('activity'), bytes('cart_contents_json'), bytes(JSON.generate(cart)))
  write_batch.add(put)

  if write_batch.size >= 250
    hbase_table.put(write_batch)
    write_batch.clear
  end

  if ((index + 1) % 5_000).zero?
    puts "  #{index + 1}/#{sessions.length} sessions loaded"
  end
end

hbase_table.put(write_batch) if write_batch.size > 0
hbase_table.close

sample_user = sessions.first['user_id']
puts "\nHBase session load complete"
puts "- Loaded sessions: #{sessions.length}"
puts "- Sample user for retrieval: #{sample_user}"
puts "- Sample prefix: #{sample_user}|"
exit
