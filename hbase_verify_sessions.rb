# Diagnostic verification for the HBase session-load step.

puts 'Row count:'
count 'user_sessions'

puts "\nFirst five stored rows:"
scan 'user_sessions', { LIMIT => 5 }
exit
