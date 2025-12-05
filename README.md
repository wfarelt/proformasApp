# proformasApp

# pip freeze
python -m pip freeze > requirements.txt
python -m pip install -r requirements.txt

# collectstatic

python manage.py collectstatic

# Añadir Compañy id a las proformas
python manage.py shell
from core.models import Proforma , Company 

company = Company.objects.get(id=1) 
print(company)
Proforma.objects.update(company=company) 
exit()