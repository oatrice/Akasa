import sys
import os

# เพิ่ม project root เข้า sys.path เพื่อให้ pytest หา module 'app' ได้
sys.path.insert(0, os.path.dirname(__file__))
