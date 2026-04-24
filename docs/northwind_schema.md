# Northwind Schema Survey

Generated from the live PostgreSQL Northwind database used by Querionyx.

## Summary

- Total tables: 14
- Core tables identified: 8

## Core Tables

- categories: present, approx. 8 rows
- products: present, approx. 77 rows
- suppliers: present, approx. 29 rows
- customers: present, approx. 91 rows
- orders: present, approx. 830 rows
- order_details: present, approx. 2155 rows
- employees: present, approx. 9 rows
- shippers: present, approx. 6 rows

## Tables and Columns

### categories (core)

| Column | Data Type | Nullable |
| --- | --- | --- |
| category_id | smallint | NO |
| category_name | character varying | NO |
| description | text | YES |
| picture | bytea | YES |

### customer_customer_demo (auxiliary)

| Column | Data Type | Nullable |
| --- | --- | --- |
| customer_id | character varying | NO |
| customer_type_id | character varying | NO |

### customer_demographics (auxiliary)

| Column | Data Type | Nullable |
| --- | --- | --- |
| customer_type_id | character varying | NO |
| customer_desc | text | YES |

### customers (core)

| Column | Data Type | Nullable |
| --- | --- | --- |
| customer_id | character varying | NO |
| company_name | character varying | NO |
| contact_name | character varying | YES |
| contact_title | character varying | YES |
| address | character varying | YES |
| city | character varying | YES |
| region | character varying | YES |
| postal_code | character varying | YES |
| country | character varying | YES |
| phone | character varying | YES |
| fax | character varying | YES |

### employee_territories (auxiliary)

| Column | Data Type | Nullable |
| --- | --- | --- |
| employee_id | smallint | NO |
| territory_id | character varying | NO |

### employees (core)

| Column | Data Type | Nullable |
| --- | --- | --- |
| employee_id | smallint | NO |
| last_name | character varying | NO |
| first_name | character varying | NO |
| title | character varying | YES |
| title_of_courtesy | character varying | YES |
| birth_date | date | YES |
| hire_date | date | YES |
| address | character varying | YES |
| city | character varying | YES |
| region | character varying | YES |
| postal_code | character varying | YES |
| country | character varying | YES |
| home_phone | character varying | YES |
| extension | character varying | YES |
| photo | bytea | YES |
| notes | text | YES |
| reports_to | smallint | YES |
| photo_path | character varying | YES |

### order_details (core)

| Column | Data Type | Nullable |
| --- | --- | --- |
| order_id | smallint | NO |
| product_id | smallint | NO |
| unit_price | real | NO |
| quantity | smallint | NO |
| discount | real | NO |

### orders (core)

| Column | Data Type | Nullable |
| --- | --- | --- |
| order_id | smallint | NO |
| customer_id | character varying | YES |
| employee_id | smallint | YES |
| order_date | date | YES |
| required_date | date | YES |
| shipped_date | date | YES |
| ship_via | smallint | YES |
| freight | real | YES |
| ship_name | character varying | YES |
| ship_address | character varying | YES |
| ship_city | character varying | YES |
| ship_region | character varying | YES |
| ship_postal_code | character varying | YES |
| ship_country | character varying | YES |

### products (core)

| Column | Data Type | Nullable |
| --- | --- | --- |
| product_id | smallint | NO |
| product_name | character varying | NO |
| supplier_id | smallint | YES |
| category_id | smallint | YES |
| quantity_per_unit | character varying | YES |
| unit_price | real | YES |
| units_in_stock | smallint | YES |
| units_on_order | smallint | YES |
| reorder_level | smallint | YES |
| discontinued | integer | NO |

### region (auxiliary)

| Column | Data Type | Nullable |
| --- | --- | --- |
| region_id | smallint | NO |
| region_description | character varying | NO |

### shippers (core)

| Column | Data Type | Nullable |
| --- | --- | --- |
| shipper_id | smallint | NO |
| company_name | character varying | NO |
| phone | character varying | YES |

### suppliers (core)

| Column | Data Type | Nullable |
| --- | --- | --- |
| supplier_id | smallint | NO |
| company_name | character varying | NO |
| contact_name | character varying | YES |
| contact_title | character varying | YES |
| address | character varying | YES |
| city | character varying | YES |
| region | character varying | YES |
| postal_code | character varying | YES |
| country | character varying | YES |
| phone | character varying | YES |
| fax | character varying | YES |
| homepage | text | YES |

### territories (auxiliary)

| Column | Data Type | Nullable |
| --- | --- | --- |
| territory_id | character varying | NO |
| territory_description | character varying | NO |
| region_id | smallint | NO |

### us_states (auxiliary)

| Column | Data Type | Nullable |
| --- | --- | --- |
| state_id | smallint | NO |
| state_name | character varying | YES |
| state_abbr | character varying | YES |
| state_region | character varying | YES |

## Foreign Keys

| Table | Column | References | Reference Column | Constraint |
| --- | --- | --- | --- | --- |
| customer_customer_demo | customer_id | customers | customer_id | fk_customer_customer_demo_customers |
| customer_customer_demo | customer_type_id | customer_demographics | customer_type_id | fk_customer_customer_demo_customer_demographics |
| employee_territories | employee_id | employees | employee_id | fk_employee_territories_employees |
| employee_territories | territory_id | territories | territory_id | fk_employee_territories_territories |
| employees | reports_to | employees | employee_id | fk_employees_employees |
| order_details | order_id | orders | order_id | fk_order_details_orders |
| order_details | product_id | products | product_id | fk_order_details_products |
| orders | customer_id | customers | customer_id | fk_orders_customers |
| orders | employee_id | employees | employee_id | fk_orders_employees |
| orders | ship_via | shippers | shipper_id | fk_orders_shippers |
| products | category_id | categories | category_id | fk_products_categories |
| products | supplier_id | suppliers | supplier_id | fk_products_suppliers |
| territories | region_id | region | region_id | fk_territories_region |

## Notes

- All columns were read directly from information_schema.
- Row counts are approximate and come from pg_stat_user_tables.
- The eight core tables are the main focus for schema linking and Text-to-SQL evaluation.
