INSERT INTO organizations (name, description) VALUES
    ('Школа языков', 'Языковая школа'),
    ('Недвижимость', 'Объекты недвижимости')
ON CONFLICT (name) DO NOTHING;

INSERT INTO categories (organization_id, name, type)
SELECT o.id, c.name, c.type
FROM organizations o
CROSS JOIN (VALUES
    ('Образование', 'income'),
    ('Аренда', 'income'),
    ('Прочее', 'income'),
    ('Зарплата Tch', 'expense'),
    ('Зарплата', 'expense'),
    ('Уборка', 'expense'),
    ('Ремонт хоз', 'expense'),
    ('Электричество', 'expense'),
    ('Аренда', 'expense'),
    ('Коммуналка', 'expense'),
    ('Налоги', 'expense'),
    ('Комиссии', 'expense'),
    ('Прочее', 'expense')
) AS c(name, type)
ON CONFLICT (organization_id, name, type) DO NOTHING;
