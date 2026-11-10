# Final Project Part 1 — retrieve sessions for a user by row-key prefix.
# Replace the command-line user id when running this script.

user_id = ARGV[0]
raise 'Usage: hbase shell hbase_query_user_sessions.rb user_000001' if user_id.nil? || user_id.empty?

prefix = "#{user_id}|"
scan 'user_sessions', {
  # HBase creates the exact start/stop range from this user-id prefix.
  ROWPREFIXFILTER => prefix,
  COLUMNS => [
    'meta:session_id', 'meta:start_time', 'meta:duration_seconds',
    'meta:conversion_status', 'meta:referrer', 'device:type',
    'device:os', 'activity:page_view_count', 'activity:cart_item_count'
  ]
}
exit
