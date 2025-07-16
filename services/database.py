from pgconnect import Connection,Column,DataType,Table

from settings.config import DatabaseConfig
from services.logging import logger

connection = Connection(
    host=DatabaseConfig.HOST,
    port=DatabaseConfig.PORT,
    user=DatabaseConfig.USER,
    password=DatabaseConfig.PASSWORD,
    database=DatabaseConfig.DATABASE,
    reconnect=True,
    pool=DatabaseConfig.POOL
)

# scheama for a gym management system

users = Table(
    name="users",
    connection=connection,
    columns=[
        Column(name="id",type=DataType.SERIAL().primary_key().unique().not_null()),

        Column(name="card_id",type=DataType.VARCHAR(length=255).unique()),

        Column(name="full_name",type=DataType.VARCHAR(length=255)),
        Column(name="username",type=DataType.VARCHAR(length=255).unique()),

        Column(name="email",type=DataType.VARCHAR(length=255).unique().not_null()),
        Column(name="phone",type=DataType.VARCHAR(length=255).unique()),

        Column(name="email_verified",type=DataType.BOOLEAN().default('false')),
        Column(name="phone_verified",type=DataType.BOOLEAN().default('false')),

        Column(name="password",type=DataType.VARCHAR(length=255)),

        Column(name="role",type=DataType.VARCHAR(length=255).not_null().default('user')),

        Column(name="avatar_url",type=DataType.VARCHAR(length=255)),

        Column(name="balance",type=DataType.DOUBLE_PRECISION().default('0.0')),

        Column(name="routine",type=DataType.TEXT()), # User's workout routine in text format



        Column(name="membership_active",type=DataType.BOOLEAN().default('false')), # whether the user has an active membership

        Column(name="membership_type",type=DataType.VARCHAR(length=255).default('basic')), # can be basic, premium, vip, etc.

        Column(name="membership_start_date",type=DataType.TIMESTAMPTZ()), # start date for the membership
        Column(name="membership_end_date",type=DataType.TIMESTAMPTZ()), # end date for the membership

        Column(name="membership_payment_cycle",type=DataType.VARCHAR(length=255).default('monthly')), # can be monthly, yearly, etc. or 6 Months, 1 Year, etc.

        Column(name="membership_renewal_date",type=DataType.TIMESTAMPTZ()), # renewal date for the membership
        Column(name="membership_renewal_price",type=DataType.DOUBLE_PRECISION().default('0.0')), # renewal price for the membership
        Column(name="membership_renewal_by",type=DataType.VARCHAR(length=255).default('user')), # can be user or admin




        Column(name="membership_cancelled",type=DataType.BOOLEAN().default('false')),
        Column(name="membership_cancelled_reason",type=DataType.VARCHAR(length=255)),
        Column(name="membership_cancelled_at",type=DataType.TIMESTAMPTZ()),
        Column(name="membership_cancelled_by",type=DataType.VARCHAR(length=255)),

        Column(name="last_login",type=DataType.TIMESTAMPTZ()),
        Column(name="updated_at",type=DataType.TIMESTAMPTZ()),
        Column(name="created_at",type=DataType.TIMESTAMPTZ().default('CURRENT_TIMESTAMP'))
    ],
    cache=True,
    cache_key="id",
    cache_ttl=5,
    cache_maxsize=1000
)

sessions = Table(
    name="sessions",
    connection=connection,
    columns=[
        Column(name="id", type=DataType.SERIAL().primary_key().unique().not_null()),
        Column(name="user_id", type=DataType.BIGINT().not_null()),  # Foreign key to users table

        Column(name="ip", type=DataType.VARCHAR(length=255).not_null()),
        Column(name="country", type=DataType.VARCHAR(length=255)),
        Column(name="country_flag", type=DataType.VARCHAR(length=255)),
        Column(name="country_code", type=DataType.VARCHAR(length=10)),
        Column(name="location", type=DataType.VARCHAR(length=255)),

        Column(name="session_token", type=DataType.VARCHAR(length=255).unique().not_null()),
        Column(name="expires_at", type=DataType.TIMESTAMPTZ().not_null()),
        Column(name="created_at", type=DataType.TIMESTAMPTZ().default('CURRENT_TIMESTAMP'))
    ],
    cache=True,
    cache_key="id",
    cache_ttl=5,
    cache_maxsize=1000
)

payments = Table(
    name="payments",
    connection=connection,
    columns=[
        Column(name="id", type=DataType.SERIAL().primary_key().unique().not_null()),
        Column(name="user_id", type=DataType.BIGINT().not_null()),  # Foreign key to users table

        Column(name="amount", type=DataType.DOUBLE_PRECISION().not_null()),
        Column(name="currency", type=DataType.VARCHAR(length=10).not_null()),

        Column(name="payment_method", type=DataType.VARCHAR(length=255).not_null()),
        Column(name="transaction_id", type=DataType.VARCHAR(length=255).unique().not_null()),
        
        Column(name="note", type=DataType.TEXT()),  # e.g., payment for membership, donation, etc.

        Column(name="status", type=DataType.VARCHAR(length=50).not_null()),  # e.g., pending, completed, failed
        Column(name="updated_by", type=DataType.VARCHAR(length=255)),  # e.g., user, admin
        Column(name="updated_at", type=DataType.TIMESTAMPTZ()),
        Column(name="created_at", type=DataType.TIMESTAMPTZ().default('CURRENT_TIMESTAMP'))
    ],
    cache=True,
    cache_key="id",
    cache_ttl=5,
    cache_maxsize=1000
)

verify_email_codes = Table(
    name="verify_email_codes",
    connection=connection,
    columns=[
        Column(name="id",type=DataType.SERIAL().primary_key().unique().not_null()),
        Column(name="user_id",type=DataType.BIGINT().not_null()),
        Column(name="code",type=DataType.VARCHAR(length=255).not_null()),
        Column(name="expired_at",type=DataType.TIMESTAMPTZ()),
        Column(name="updated_at",type=DataType.TIMESTAMPTZ()),
        Column(name="created_at",type=DataType.TIMESTAMPTZ().default('CURRENT_TIMESTAMP')),
    ],
    cache=True,
    cache_key="id",
    cache_ttl=300,
    cache_maxsize=1000
)

async def InitDatabase():
    await users.create()
    logger.success("Users table created successfully")
    await sessions.create()
    logger.success("Sessions table created successfully")
    await payments.create()
    logger.success("Payments table created successfully")
    await verify_email_codes.create()
    logger.success("Verify email codes table created successfully")