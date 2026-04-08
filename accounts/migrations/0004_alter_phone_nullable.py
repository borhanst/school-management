from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_phone_unique"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE accounts_user_new AS SELECT * FROM accounts_user;
                DROP TABLE accounts_user;
                CREATE TABLE "accounts_user" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "password" varchar(128) NOT NULL,
                    "last_login" datetime NULL,
                    "is_superuser" bool NOT NULL,
                    "username" varchar(150) NOT NULL UNIQUE,
                    "first_name" varchar(150) NOT NULL,
                    "last_name" varchar(150) NOT NULL,
                    "email" varchar(254) NOT NULL,
                    "is_staff" bool NOT NULL,
                    "is_active" bool NOT NULL,
                    "date_joined" datetime NOT NULL,
                    "role" varchar(20) NOT NULL,
                    "phone" varchar(20) NULL,
                    "address" text NOT NULL,
                    "photo" varchar(100) NULL,
                    "gender" varchar(10) NOT NULL,
                    "blood_group" varchar(5) NOT NULL,
                    "date_of_birth" date NULL
                );
                INSERT INTO accounts_user SELECT
                    id, password, last_login, is_superuser, username,
                    first_name, last_name, email, is_staff, is_active,
                    date_joined, role,
                    CASE WHEN phone = '' THEN NULL ELSE phone END,
                    address, photo, gender, blood_group, date_of_birth
                FROM accounts_user_new;
                DROP TABLE accounts_user_new;
                CREATE UNIQUE INDEX accounts_user_phone_unique
                    ON accounts_user (phone) WHERE phone IS NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
