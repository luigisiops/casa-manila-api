# Casa Manila API

A Django REST Framework API for managing casa manila food orders with PostgreSQL database and Docker support.

## Prerequisites

- Docker and Docker Compose installed
- Git

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/luigisiops/casa-manila-api.git
cd casa-manila-api/casa_manila_api
```

### 2. Create environment file
Copy the example environment variables:
```bash
cp .env.example .env
```

Edit `.env` and set your configuration:
```
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=db-name
DB_USER=db-user
DB_PASSWORD=your-secure-password
DB_HOST=postgres
DB_PORT=5432
```

### 3. Start the application with Docker
```bash
docker compose up -d
```

This will:
- Build the Django application container
- Start PostgreSQL database container
- Run migrations automatically
- Start the Django development server

### 4. Access the application

**API**: http://localhost:8000/
**Admin Panel**: http://localhost:8000/admin/

## Common Commands

### Create a superuser (admin account)
```bash
docker compose exec django python manage.py createsuperuser
```

### Run migrations
```bash
docker compose exec django python manage.py migrate
```

### Create database migrations
```bash
docker compose exec django python manage.py makemigrations
```

### Create migrations and apply them
```bash
docker compose exec django python manage.py makemigrations
docker compose exec django python manage.py migrate
```

### View logs
```bash
docker compose logs django      # Django logs
docker compose logs postgres    # PostgreSQL logs
docker compose logs -f          # Follow logs in real-time
```

### Interactive Python shell
```bash
docker compose exec django python manage.py shell
```

### Connect to PostgreSQL database
```bash
docker compose exec postgres psql -U casa_manila -d casa_manila
```

### Stop the application
```bash
docker compose down
```

### Reset database (removes all data)
```bash
docker compose down -v
docker compose up -d
```

## Project Structure

```
casa-manila-api/
├── config/                  # Django configuration
│   ├── settings.py         # Settings file
│   ├── urls.py             # Main URL routes
│   ├── wsgi.py
│   └── asgi.py
├── menu/              # Django app
│   ├── models.py           # Database models
│   ├── views.py            # API views
│   ├── serializers.py      # DRF serializers
│   └── ...
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
├── .env                    # Environment variables (not tracked)
├── .gitignore              # Git ignore rules
└── README.md              # This file
```

## API Endpoints

### Food Items
- `GET /api/food-items/` - List all active food items
- `POST /api/food-items/` - Create a new food item
- `GET /api/food-items/{id}/` - Get a specific food item
- `PUT /api/food-items/{id}/` - Update a food item
- `DELETE /api/food-items/{id}/` - Archive a food item (soft delete, sets is_active=False)

### Item Orders
- `GET /api/item-orders/` - List all item orders
- `GET /api/item-orders/{id}/` - Get a specific item order

**Note**: Item orders can only be created through the Orders endpoint. They cannot be created directly.

### Orders
- `GET /api/orders/` - List all orders
- `POST /api/orders/` - Create a new order with nested item orders
- `GET /api/orders/{id}/` - Get a specific order
- `PUT/PATCH /api/orders/{id}/` - Update an order and/or modify items
- `DELETE /api/orders/{id}/` - Archive an order (soft delete, sets is_active=False)

#### Query Parameters
- `pickup_date` - Filter orders by pickup date (format: YYYY-MM-DD)
- `phone_number` - Filter orders by phone number
- `search` - Combined search for pickup date and phone number (e.g., "2024-01-01+0917")

#### Creating an Order with Items
```json
{
  "pickup_datetime": "2026-01-15T14:30:00Z",
  "customer_name": "John Doe",
  "email": "john@example.com",
  "phone_number": "555-1234",
  "store_id": "location-1",
  "items": [
    {
      "item_id": 1,
      "quantity": 2
    },
    {
      "item_id": 3,
      "quantity": 1
    }
  ]
}
```

#### Updating Order Items
Use PATCH or PUT to update an order's items. The subtotal is automatically recalculated:
```json
{
  "items": [
    {
      "item_id": 1,
      "quantity": 3
    },
    {
      "item_id": 2,
      "quantity": 1
    }
  ]
}
```

**Note**: When updating with the `items` field, only the items you include will remain on the order. Items not in the list will be removed. To remove a specific item, omit it from the items list.

## Development

### Adding new dependencies
1. Update `requirements.txt`
2. Rebuild the Docker image:
```bash
docker compose build
docker compose up -d
```

### Running tests

To run all tests
```bash
docker compose exec django python manage.py test menu
```

To run specific tests
```bash
docker compose exec django python manage.py test menu.tests.FoodItemViewSetTestCase
docker compose exec django python manage.py test menu.tests.OrderViewSetTestCase
```

The tests cover:
- Active/inactive filtering for FoodItems
- Soft delete behavior
- ItemOrder read-only enforcement
- Order creation with items and subtotal calculation
- Order item updates and quantity modifications
- Removing items from orders
- Order deletion cascading to ItemOrders
- Search filtering by date and phone
- Model-level line_total and subtotal calculations
- Automatic subtotal recalculation on item changes

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Allowed host domains | `localhost,127.0.0.1` |
| `DB_NAME` | PostgreSQL database name | `casa_manila` |
| `DB_USER` | PostgreSQL username | `casa_manila` |
| `DB_PASSWORD` | PostgreSQL password | Required |
| `DB_HOST` | Database host | `postgres` |
| `DB_PORT` | Database port | `5432` |

## Troubleshooting

### Database connection errors
```bash
# Check if containers are running
docker compose ps

# View logs
docker compose logs postgres

# Reset database
docker compose down -v
docker compose up -d
```

### Port already in use
Change ports in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Change 8000 to another port
```

### Django migrations issues
```bash
docker compose exec django python manage.py migrate --fake-initial
```

## License

[Your License Here]

## Contact

For issues or questions, please create an issue on GitHub.
