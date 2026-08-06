INSERT INTO organizations (name, description) VALUES
    ('Школа языков', 'Языковая школа'),
    ('Недвижимость', 'Объекты недвижимости')
ON CONFLICT (name) DO NOTHING;

INSERT INTO categories (organization_id, name, type)
SELECT o.id, c.name, c.type
FROM organizations o
CROSS JOIN (VALUES
    ('Аренда', 'income'),
    ('Материалы', 'expense'),
    ('Коммунальные', 'expense'),
    ('Зарплата', 'expense'),
    ('Прочее', 'expense')
) AS c(name, type)
ON CONFLICT (organization_id, name) DO NOTHING;
