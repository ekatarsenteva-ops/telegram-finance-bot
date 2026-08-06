-- Объекты (организации)
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Пользователи
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'coordinator'
        CHECK (role IN ('owner', 'admin', 'coordinator', 'viewer')),
    default_organization_id INTEGER REFERENCES organizations(id),
    default_currency VARCHAR(3) DEFAULT 'RUB',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Категории (привязаны к объектам)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('income', 'expense')),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (organization_id, name)
);

-- Контрагенты (глобальные, без привязки к объекту)
CREATE TABLE counterparties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Транзакции (основная таблица)
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    type VARCHAR(20) NOT NULL CHECK (type IN ('income', 'expense', 'incoming_payment')),
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'RUB',
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    category_id INTEGER REFERENCES categories(id),
    counterparty_id INTEGER REFERENCES counterparties(id),

    is_offset BOOLEAN NOT NULL DEFAULT FALSE,
    offset_status VARCHAR(20) CHECK (offset_status IN ('pending', 'applied')),

    raw_ai_log JSONB,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Участники групповых расходов (отслеживание возврата)
CREATE TABLE expense_participants (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    person_name VARCHAR(255) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    is_paid BOOLEAN NOT NULL DEFAULT FALSE,
    paid_date TIMESTAMP,
    paid_amount NUMERIC(12, 2),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Взаимозачёты (отслеживание статуса)
CREATE TABLE counterparty_offsets (
    id SERIAL PRIMARY KEY,
    source_transaction_id INTEGER NOT NULL REFERENCES transactions(id),
    counterparty_id INTEGER NOT NULL REFERENCES counterparties(id),
    amount NUMERIC(12, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'applied', 'cancelled')),
    applied_to_transaction_id INTEGER REFERENCES transactions(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_transactions_user_created ON transactions (user_id, created_at);
CREATE INDEX idx_expense_participants_is_paid ON expense_participants (is_paid);
CREATE INDEX idx_counterparty_offsets_status ON counterparty_offsets (status);
