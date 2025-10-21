from multiprocessing import Process
import os

def run_customer():
    os.system("python customer/customer_service.py")

def run_product():
    os.system("python product/product_service.py")

def run_inventory():
    os.system("python inventory/inventory_service.py")

def run_order():
    os.system("python order/order_service.py")
    
def run_payment():
    os.system("python payment/payment_service.py")

def run_gateway():
    os.system("python api_gateway/api_gateway.py")

if __name__ == '__main__':
    services = [run_customer, run_product, run_inventory, run_order,run_payment, run_gateway]
    processes = [Process(target=srv) for srv in services]
    
    for p in processes:
        p.start()
    
    for p in processes:
        p.join()
