"""
KairaFlow Setup Script
Run this script to initialize the database and create default admin user
"""

from app.utils.database import init_database
from app.models.user import User

def setup():
    print("🚀 Setting up KairaFlow...")
    
    # Initialize database
    print("\n📊 Initializing database...")
    init_database()
    
    # Create admin user
    print("\n👤 Creating admin user...")
    try:
        admin_id = User.create(
            name='Admin User',
            email='admin@agency.com',
            password='admin123',
            role='admin',
            phone='1234567890'
        )
        print(f"✅ Admin user created (ID: {admin_id})")
        print("   Email: admin@agency.com")
        print("   Password: admin123")
    except Exception as e:
        print(f"⚠️  Admin user might already exist: {e}")
    
    # Create sample users
    print("\n👥 Creating sample users...")
    
    sample_users = [
        ('John Marketing', 'john@agency.com', 'password123', 'marketing_head', '1234567891'),
        ('Jane Developer', 'jane@agency.com', 'password123', 'developer', '1234567892'),
        ('Mike Social', 'mike@agency.com', 'password123', 'smm', '1234567893'),
        ('Sarah Sales', 'sarah@agency.com', 'password123', 'crm', '1234567894'),
    ]
    
    for name, email, password, role, phone in sample_users:
        try:
            user_id = User.create(name, email, password, role, phone)
            print(f"✅ Created {role}: {email}")
        except Exception as e:
            print(f"⚠️  User {email} might already exist")
    
    print("\n✨ Setup complete!")
    print("\n🌐 Next steps:")
    print("1. Start backend: python app.py")
    print("2. Start frontend: cd ../frontend && npm install && npm run dev")
    print("3. Open http://localhost:3000")
    print("4. Login with admin@agency.com / admin123")

if __name__ == "__main__":
    setup()
