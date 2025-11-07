-- Insertar cliente si no existe
INSERT INTO clients (name, email) 
VALUES ('Test Client', 'test@example.com')
ON CONFLICT (email) DO NOTHING;

-- Insertar datos de prueba en processed_data
INSERT INTO processed_data (source_type, data)
VALUES 
    ('test', '{"text": "This product is excellent and I love it very much"}'),
    ('test', '{"text": "Terrible experience, very disappointed with the service"}'),
    ('test', '{"text": "The quality is good but the price is too high"}'),
    ('test', '{"text": "Amazing features and great customer support team"}'),
    ('test', '{"text": "Not recommended, poor quality and bad design"}'),
    ('test', '{"text": "Artificial intelligence is transforming the industry"}'),
    ('test', '{"text": "Machine learning algorithms improve prediction accuracy"}'),
    ('test', '{"text": "The standard product meets basic requirements"}'),
    ('test', '{"text": "Outstanding performance and innovative technology"}'),
    ('test', '{"text": "Disappointing results and frequent technical issues"}');
