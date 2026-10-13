/*
===============================================================================
Sequence Metadata
===============================================================================
*/

SELECT
    sequence_schema,
    sequence_name,
    data_type,
    start_value,
    minimum_value,
    maximum_value,
    increment
FROM information_schema.sequences
WHERE sequence_schema = 'walmart_db'
ORDER BY sequence_name;
