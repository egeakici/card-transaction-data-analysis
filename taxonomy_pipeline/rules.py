"""Versioned, conservative rules. No model training and no invented ground truth."""
import csv, re, unicodedata
from functools import lru_cache
from pathlib import Path
from collections import defaultdict

VERSION='1.0.0'
TAXONOMY={
'FOOD_AND_DRINK':'restaurants fast_food coffee_shops bars_and_pubs bakeries catering food_delivery',
'GROCERIES':'supermarkets discount_grocery convenience_and_liquor_stores specialty_food wholesale_clubs',
'GENERAL_MERCHANDISE':'online_marketplaces superstores_and_department_stores discount_and_variety_stores clothing_and_accessories electronics_and_computers books_and_media sporting_goods_toys_and_hobby pet_supplies gifts_and_specialty_retail',
'HOME_AND_GARDEN':'home_improvement_and_hardware garden_and_nursery furniture_and_appliances home_and_building_services',
'HEALTH_AND_MEDICAL':'medical_care pharmacies dental_and_eye_care veterinary',
'PERSONAL_CARE':'beauty_fitness_and_wellness laundry_and_clothing_care',
'TRANSPORTATION':'fuel_and_ev_charging public_transit_and_rail taxis_and_rideshare parking tolls_and_road_charges vehicle_maintenance_and_parts vehicle_dealers transportation_services_other',
'TRAVEL':'airlines lodging car_rental travel_agencies_and_tours',
'ENTERTAINMENT_AND_RECREATION':'events_and_live_entertainment attractions_and_recreation gambling',
'UTILITIES_AND_TELECOM':'energy_utilities water_and_waste phone_and_mobile internet_and_tv',
'SOFTWARE_AND_DIGITAL':'software_and_apps digital_media_and_games online_subscriptions',
'EDUCATION':'schools_and_universities training_and_courses exams_and_certification',
'BUSINESS_SUPPLIES_AND_EQUIPMENT':'office_supplies_and_stationery industrial_and_mro_supplies medical_and_lab_supplies office_and_commercial_equipment uniforms_and_workwear',
'PROFESSIONAL_AND_BUSINESS_SERVICES':'advertising_and_marketing printing_and_publishing it_services_and_hosting professional_services business_support_services shipping_and_logistics',
'GOVERNMENT_AND_NONPROFIT':'government_fees_and_fines charities_and_donations memberships_and_associations',
'FINANCIAL_SERVICES':'insurance financial_services_and_fees'}
PARENT={child:parent for parent,children in TAXONOMY.items() for child in children.split()}
LABELS=[parent+'.'+child for child,parent in PARENT.items()]
STATUSES=['UNRESOLVED_INSUFFICIENT_EVIDENCE','UNRESOLVED_AMBIGUOUS','UNRESOLVED_OUT_OF_TAXONOMY','NOT_A_TRANSACTION']
def label(child): return PARENT[child]+'.'+child
@lru_cache(maxsize=250000)
def norm(value):
    text=unicodedata.normalize('NFKD',str(value or '')).encode('ascii','ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]+',' ',text.replace('&',' AND ')).strip()

# MCCs which combine several leaves deliberately have no single forced label.
CODE_GROUPS={
'restaurants':'5812', 'fast_food':'5814','bars_and_pubs':'5813','bakeries':'5462','catering':'5811',
'supermarkets':'5411','convenience_and_liquor_stores':'5921','specialty_food':'5422 5441 5451','wholesale_clubs':'5300',
'online_marketplaces':'5262','superstores_and_department_stores':'5311',
'discount_and_variety_stores':'5310 5331','clothing_and_accessories':'5094 5131 5611 5621 5631 5641 5651 5661 5681 5691 5699 5931 5944',
'electronics_and_computers':'4812 5045 5723 5732 5733', 'books_and_media':'5192 5735 5942 5994',
'sporting_goods_toys_and_hobby':'5655 5940 5941 5945 5946 5949 5970 5971',
'pet_supplies':'5995','gifts_and_specialty_retail':'5309 5932 5937 5947 5948 5972 5973 5978 5993 5998 5999',
'home_improvement_and_hardware':'5039 5198 5200 5211 5231 5251 5713 5714 5718 5996',
'garden_and_nursery':'5261 5193 5992','furniture_and_appliances':'5712 5719 5722',
'home_and_building_services':'0780 1520 1711 1731 1740 1750 1761 1771 1799 7342 7349 7623 7629 7641 7692 7699',
'medical_care':'4119 5975 5976 8011 8031 8041 8049 8050 8062 8099',
'pharmacies':'5122 5912','dental_and_eye_care':'8021 8042 8043 8044','veterinary':'0742',
'beauty_fitness_and_wellness':'5977 7230 7297 7298 7997', 'laundry_and_clothing_care':'5697 7210 7211 7216 7217 7251 7276',
'fuel_and_ev_charging':'5172 5299 5541 5542 5552 5983',
'public_transit_and_rail':'4111 4112 4131','taxis_and_rideshare':'4121','parking':'7523',
'tolls_and_road_charges':'4784','vehicle_maintenance_and_parts':'5013 5531 5532 5533 7531 7534 7535 7538 7542 7549',
'vehicle_dealers':'5511 5521 5551 5561 5571 5592 5598 5599',
'transportation_services_other':'4457 4468 4582 4789','airlines':'4511','lodging':'7011 7012 7032 7033',
'car_rental':'7512','travel_agencies_and_tours':'4722 4723',
'events_and_live_entertainment':'7832 7922 7929 7932 7998',
'attractions_and_recreation':'7933 7941 7991 7992 7993 7994 7996 7999','gambling':'7800 7801 7802 7995 9406',
'phone_and_mobile':'4813 4814 4821','internet_and_tv':'4899',
'software_and_apps':'5734','digital_media_and_games':'5815 5816 5817 5818',
'schools_and_universities':'8211 8220','training_and_courses':'8241 8244 8249 8299',
'office_supplies_and_stationery':'5111 5943','industrial_and_mro_supplies':'2842 5051 5065 5072 5074 5085 5169 5997',
'medical_and_lab_supplies':'5047 8071','office_and_commercial_equipment':'5021 5044 5046 5974',
'uniforms_and_workwear':'5137 5139',
'advertising_and_marketing':'7311 5967','printing_and_publishing':'2741 2791 7332 7338 7339',
'it_services_and_hosting':'4816 7372 7375 7379 7622','professional_services':'7321 7322 7333 7336 7361 7392 7393 7394 7395 8111 8911 8931 8999',
'business_support_services':'7277 7278 7296 7399','shipping_and_logistics':'4011 4214 4215 4225 9402',
'government_fees_and_fines':'9211 9222 9223 9311 9399 9405',
'charities_and_donations':'8398 8651 8661', 'memberships_and_associations':'8641 8675 8699',
'insurance':'5960 6300 6381 6399',
'financial_services_and_fees':'4829 6010 6011 6012 6050 6051 6211 6531 6532 6533 6534 6535 6536 6537 6538 6540 6611'}
CODE_MAP={code:label(child) for child,codes in CODE_GROUPS.items() for code in codes.split()}
CODE_MAP.update({'8071':label('medical_care'),'5974':label('office_supplies_and_stationery'),'7998':label('attractions_and_recreation'),'7941':label('events_and_live_entertainment')})
for _c in ['5931','7394']: CODE_MAP.pop(_c,None)
AMBIGUOUS_CODES={'4900','5499','5399','5962','5963','5964','5965','5966','5968','5969','7273','7299','7513','7519','8351','8998','5931'}
GAP_CODES={'0763','4411','5099','5199','5271','5933','5935','6513','6529','6530','7394'}
def code_label(code):
    if code in CODE_MAP: return CODE_MAP[code]
    if code.isdigit():
        n=int(code)
        if 3000<=n<=3350: return label('airlines')
        if 3351<=n<=3500: return label('car_rental')
        if 3501<=n<=3999: return label('lodging')
    return ''

# A rule is an explicit regex and target; recorded verbatim in exported rule tables.
MERCHANT_RULES=[
('food_delivery',r'\b(DELIVEROO|DOORDASH|JUST EAT|UBER EATS|GRUBHUB)\b'),
('taxis_and_rideshare',r'\b(UBER|LYFT|ADDISON LEE|TAXI|TAXIS|CAB COMPANY)\b'),
('discount_grocery',r'\b(ALDI|LIDL|SAVE A LOT|SAV A LOT|WINCO)\b'),
('wholesale_clubs',r'\b(COSTCO|SAMS CLUB|SAM S CLUB|BJ S WHOLESALE|BOOKER CASH)\b'),
('supermarkets',r'\b(TESCO|SAINSBURY|SAINSBURYS|SAINSBURY S|ASDA|MORRISONS|WAITROSE|KROGER|SAFEWAY|WHOLE FOODS|FOOD LION|PUBLIX|WEGMANS|WEGMAN|ALBERTSONS|ICELAND FOODS|OCADO|SPROUTS FARMERS)\b'),
('coffee_shops',r'\b(STARBUCKS|COSTA COFFEE|CAFFE NERO|CAFE NERO|COFFEE SHOP|COFFEE HOUSE|TIM HORTON|DUTCH BROS|DUNKIN)\b'),
('fast_food',r'\b(MCDONALD|MCDONALDS|MC DONALDS|KFC|BURGER KING|SUBWAY|TACO BELL|WENDYS|WENDY S|CHICK FIL|PIZZA HUT|DOMINOS PIZZA|DOMINO S PIZZA|PAPA JOHNS|GREGGS|FIVE GUYS|CHIPOTLE|SONIC DRIVE|DAIRY QUEEN|WHATABURGER|ARBY)\b'),
('bakeries',r'\b(BAKERY|BAKERIES|PATISSERIE)\b'),
('bars_and_pubs',r'\b(WETHERSPOON|WETHERSPOONS|GREENE KING|PUB|PUBS|PUBLIC HOUSE)\b'),
('online_marketplaces',r'\b(AMAZON|AMZN|AMZNMKTP|AMZNMKTPLACE|AMZNBUSINESS|AMAZONMKTPLC|AMZNMKTPLACE|EBAY|ETSY|ALIEXPRESS|ALIBABA|AMZ)\b'),
('superstores_and_department_stores',r'\b(WALMART|WAL MART|TARGET|JOHN LEWIS|MARKS SPENCER|MARKS AND SPENCER|MACYS|MACY S|DILLARDS|DILLARD S|DEBENHAMS|SEARS|KOHLS|KOHL S)\b'),
('discount_and_variety_stores',r'\b(ARGOS|POUNDLAND|POUNDSTRETCHER|HOME BARGAINS|B AND M|B M RETAIL|WILKO|WILKINSON|DOLLAR TREE|DOLLAR GENERAL|FAMILY DOLLAR|BIG LOTS|FIVE BELOW)\b'),
('office_supplies_and_stationery',r'\b(OFFICE DEPOT|OFFICEMAX|OFFICE MAX|STAPLES|STAPLESCONTRACTCOMMERC|STAPLS|CORPORATE EXPRESS|CORP EXPR|VIKING DIRECT|LYRECO|BANNER BUSINESS|R YMAN|RYMAN)\b'),
('electronics_and_computers',r'\b(DELL|CDW|NEWEGG|INSIGHT DIRECT|APPLE STORE|APPLE RETAIL|BEST BUY|BESTBUY|LENOVO|HP DIRECT|HEWLETT PACKARD)\b'),
('industrial_and_mro_supplies',r'\b(GRAINGER|FASTENAL|MCMASTER|MC MASTER|MSC INDUSTRIAL|ZORO|ULINE|LAWSON PRODUCTS|RS COMPONENTS|AIRGAS|GEXPRO)\b'),
('medical_and_lab_supplies',r'\b(VWR|SIGMA ALDRICH|THERMO FISHER|FISHER SCIENTIFIC|FISHER SCI|HENRY SCHEIN|MCKESSON|MEDLINE|LAB SAFETY)\b'),
('home_improvement_and_hardware',r'\b(HOME DEPOT|LOWES|LOWE S|B Q|B AND Q|SCREWFIX|TOOLSTATION|WICKES|TRAVIS PERKINS|JEWSON|ACE HARDWARE|HARBOR FREIGHT|MENARDS)\b'),
('furniture_and_appliances',r'\b(IKEA|AO RETAIL|ASHLEY FURNITURE|APPLIANCES DIRECT)\b'),
('vehicle_maintenance_and_parts',r'\b(NAPA AUTO|AUTOZONE|AUTO ZONE|O REILLY AUTO|OREILLY AUTO|ADVANCE AUTO|HALFORDS|KWIK FIT|FIRESTONE|GOODYEAR)\b'),
('pet_supplies',r'\b(PETSMART|PETCO|PETS AT HOME|CHEWY)\b'),
('pharmacies',r'\b(BOOTS|WALGREENS|CVS PHARMACY|RITE AID|LLOYDS PHARMACY)\b'),
('fuel_and_ev_charging',r'\b(SHELL|CHEVRON|EXXON|TEXACO|TEXACO|PHILLIPS 66|CONOCO|QUIKTRIP|QUIK TRIP|MURPHY USA|BP CONNECT|BP OIL|BP FUEL|TESLA SUPERCHARGER|CHARGEPOINT|EVGO)\b'),
('public_transit_and_rail',r'\b(TRAINLINE|TRAIN LINE|NATIONAL RAIL|NORTHERN RAIL|CROSSCOUNTRY|CROSS COUNTRY TRAINS|GREAT WESTERN RAIL|LNER|VIRGIN TRAINS|TRANSPORT FOR LONDON|TFL|NATIONAL EXPRESS|STAGECOACH|MEGABUS)\b'),
('parking',r'\b(RINGGO|RING GO|NCP|NATIONAL CAR PARK|PARKING|PAYBYPHONE|JUSTPARK|APCOA)\b'),
('tolls_and_road_charges',r'\b(PIKEPASS|TURNPIKE|TOLL|TOLLS|DART CHARGE|CONGESTION CHARGE)\b'),
('airlines',r'\b(SOUTHWEST AIR|SOUTHWESTAIR|AMERICAN AIR|UNITED AIR|DELTA AIR|BRITISH AIRWAYS|EASYJET|RYANAIR|JET2|LUFTHANSA|AIR FRANCE|KLM|EMIRATES|QATAR AIR)\b'),
('lodging',r'\b(HOTEL|HOTELS|MOTEL|MOTELS|HILTON|MARRIOTT|TRAVELODGE|PREMIER INN|HAMPTON INN|HAMPTON INNS|HOLIDAY INN|DRURY|HYATT|SHERATON|BEST WESTERN|RESIDENCE INN|COMFORT INN|QUALITY INN|DOUBLETREE|AIRBNB|TRIVAGO|IBIS|RADISSON|BOOKING COM)\b'),
('car_rental',r'\b(ENTERPRISE RENT|HERTZ|AVIS|BUDGET RENT|NATIONAL CAR RENTAL|ALAMO RENT|EUROPCAR|SIXT)\b'),
('shipping_and_logistics',r'\b(FEDEX|FED EX|ROYAL MAIL|ROYALMAIL|POST OFFICE|USPS|UNITED PARCEL|DHL|PARCELFORCE|PARCEL FORCE)\b'),
('advertising_and_marketing',r'\b(FACEBK|FACEBOOK|META ADS|GOOGLE ADS|GOOGLE ADWORDS|MAILCHIMP|LINKEDIN ADS)\b'),
('software_and_apps',r'\b(ADOBE|MICROSOFT|MSFT|AUTODESK|ZOOM US|ZOOM COM|ZOOM VIDEO|SLACK|DROPBOX|CANVA|ATLASSIAN|GITHUB|GITLAB|INTUIT|SURVEYMONKEY|SURVEY MONKEY|DOCUSIGN|OPENAI|CHATGPT|SALESFORCE)\b'),
('digital_media_and_games',r'\b(NETFLIX|SPOTIFY|AUDIBLE|STEAMGAMES|STEAM GAMES|PLAYSTATION|XBOX|NINTENDO|KINDLE|APPLE MUSIC|DISNEY PLUS|DISNEYPLUS)\b'),
('online_subscriptions',r'\b(FINANCIAL TIMES SUBSCRIPTION|FT SUBSCRIPTION)\b'),
('it_services_and_hosting',r'\b(GODADDY|GO DADDY|123 REG|FASthosts|IONOS|DIGITALOCEAN|AWS|AMAZON WEB SERVICES|GOOGLE CLOUD|HOSTGATOR|BLUEHOST|SITEGROUND|CLOUDFLARE)\b'),
('water_and_waste',r'\b(THAMES WATER|SEVERN TRENT|NORTHUMBRIAN WATER|UNITED UTILITIES|WATER BILL|WATER UTILITY|WASTE MANAGEMENT|REPUBLIC SERVICES|VEOLIA|BIFFA)\b'),
('energy_utilities',r'\b(BRITISH GAS|EDF ENERGY|EON ENERGY|E ON ENERGY|OCTOPUS ENERGY|DUKE ENERGY|OKLAHOMA GAS|OG E|PUBLIC SERVICE CO|SCOTTISH POWER|NPOWER)\b'),
('phone_and_mobile',r'\b(VODAFONE|O2|EE LIMITED|BT GROUP|BT PAYMENT|BRITISH TELECOM|VERIZON|AT T|ATT BUS PHONE|ATT MOBILITY|T MOBILE|GIFFGAFF|THREE MOBILE)\b'),
('internet_and_tv',r'\b(VIRGIN MEDIA|SKY DIGITAL|SKY SUBS|COMCAST|XFINITY|COX COMMUNICATION)\b'),
('government_fees_and_fines',r'\b(UKVI|DVLA|HMCTS|HMRC|GOV UK|PASSPORT OFFICE|COMPANIES HOUSE|DBS|POLICE VETTING|POLICE VETTIN|WARKS POLICE)\b'),
('insurance',r'\b(INSURANCE|INSURANCES|GEICO|PROGRESSIVE INS|AVIVA|AXA|ALLIANZ|ADMIRAL INS)\b'),
('financial_services_and_fees',r'\b(CASH ADVANCE FEE|PURCH FEE|TRANS FEE|TRANSACTION FEE|BANK CHARGE|BANK FEE|NATWEST|BARCLAYS BANK|LLOYDS BANK)\b'),
('clothing_and_accessories',r'\b(PRIMARK|NEXT RETAIL|H M|H AND M|ZARA|TK MAXX|TJ MAXX|SPORTSDIRECT|SPORTS DIRECT)\b'),
('books_and_media',r'\b(WATERSTONES|W H SMITH|WHSMITH|BARNES NOBLE|BARNES AND NOBLE|BOOK DEPOSITORY)\b'),
]
# Purpose/product evidence: narrow, literal terms. Multiple different matches are
# marked mixed/ambiguous rather than resolved by arbitrary rule priority.
ITEM_RULES=[
('exams_and_certification',r'\b(EXAM FEE|EXAMINATION FEE|CERTIFICATION EXAM|EXAM REGISTRATION)\b'),
('training_and_courses',r'\b(TRAINING COURSE|ONLINE COURSE|CERTIFICATE COURSE|TRAINING FEE|COURSE FEE|TUITION FOR TRAINING|STAFF TRAINING|CONFERENCE REGISTRATION|SEMINAR REGISTRATION|WEBINAR REGISTRATION)\b'),
('schools_and_universities',r'\b(SCHOOL TUITION|UNIVERSITY TUITION|COLLEGE TUITION)\b'),
('government_fees_and_fines',r'\b(VISA SPONSORSHIP|VISA PAYMENT|IMMIGRATION SKILLS|PASSPORT FEE|CERTIFICATE OF SPONSORSHIP|NATIONAL VETTING SERVICE|LICENCE RENEWAL FEE|LICENSE RENEWAL FEE)\b'),
('advertising_and_marketing',r'\b(ADVERTISING CAMPAIGN|ADVERTISING DISTRIBUTION|EDUCATION CAMPAIGN|SME CAMPAIGN|SOCIAL MEDIA ADVERTISING|PUBLICITY AND PROMOTION)\b'),
('online_subscriptions',r'\b(FINANCIAL TIMES SUBSCRIPTION|ANNUAL FINANCIAL TIMES)\b'),
('software_and_apps',r'\b(SOFTWARE LICEN[CS]E|SOFTWARE SUBSCRIPTION|SOFTWARE RENEWAL|MICROSOFT OFFICE|OFFICE 365|MICROSOFT 365|ADOBE ACROBAT|ANTIVIRUS|ANTI VIRUS|ZOOM PRO|ZOOM LICEN[CS]E)\b'),
('it_services_and_hosting',r'\b(WEB HOSTING|DOMAIN RENEWAL|DOMAIN REGISTRATION|CLOUD HOSTING)\b'),
('phone_and_mobile',r'\b(MOBILE PHONE BILL|PHONE SERVICE|TELEPHONE SERVICE|MOBILE DATA PLAN|MOBILE PHONE CONTRACT)\b'),
('water_and_waste',r'\b(WATER BILL|SEWER BILL|WASTE COLLECTION|REFUSE COLLECTION|WASTE DISPOSAL SERVICE)\b'),
('energy_utilities',r'\b(ELECTRICITY BILL|GAS BILL|ELECTRIC UTILITY BILL)\b'),
('charities_and_donations',r'\b(CHARITABLE DONATION|CHARITY DONATION|CHARITABLE GRANT)\b'),
('memberships_and_associations',r'\b(PROFESSIONAL MEMBERSHIP|ASSOCIATION DUES|MEMBERSHIP FEE)\b'),
('insurance',r'\b(INSURANCE PREMIUM|INSURANCE PAYMENT)\b'),
('financial_services_and_fees',r'\b(TRANSACTION FEE|CASH ADVANCE FEE|BANK FEE|BANK CHARGE|PURCHASE FEE)\b'),
('fuel_and_ev_charging',r'\b(DIESEL FUEL|UNLEADED GASOLINE|MOTOR FUEL|PETROL PURCHASE|EV CHARGING|VEHICLE CHARGING)\b'),
('parking',r'\b(PARKING FEE|CAR PARKING|PARKING CHARGE|PARKING PERMIT)\b'),
('tolls_and_road_charges',r'\b(TOLL CHARGE|TOLL FEE|TURNPIKE TOLL|CONGESTION CHARGE)\b'),
('car_rental',r'\b(CAR RENTAL|RENTAL CAR|CAR HIRE)\b'),
('lodging',r'\b(HOTEL ROOM|HOTEL ACCOMMODATION|HOTEL BOOKING|OVERNIGHT ACCOMMODATION|HOTEL STAY)\b'),
('airlines',r'\b(AIRLINE TICKET|AIR FARE|AIRFARE|FLIGHT TICKET)\b'),
('public_transit_and_rail',r'\b(TRAIN TICKET|RAIL TICKET|BUS TICKET|BUS FARE|RAIL FARE)\b'),
('taxis_and_rideshare',r'\b(TAXI FARE|TAXI HIRE|TAXI JOURNEY)\b'),
('shipping_and_logistics',r'\b(POSTAGE STAMP|POSTAGE STAMPS|FRANKING MACHINE CREDITS|COURIER SERVICE|POSTAL SERVICE|SHIPPING FEE|FREIGHT CHARGE)\b'),
('office_supplies_and_stationery',r'\b(COPY PAPER|COPIER PAPER|PRINTING PAPER|PRINTER PAPER|PAPER A4|A4 PAPER|PAPER CLIP|PAPERCLIPS|BALLPOINT PEN|BALL POINT PEN|INK CARTRIDGE|INKJET CARTRIDGE|TONER CARTRIDGE|CARTRIDGE TONER|STAPLE REMOVER|FILE FOLDER|MANILA FOLDER)\b'),
('electronics_and_computers',r'\b(LAPTOP COMPUTER|DESKTOP COMPUTER|COMPUTER MONITOR|COMPUTER KEYBOARD|USB FLASH DRIVE|EXTERNAL HARD DRIVE|APPLE IPAD|LENOVO THINKPAD|DELL LATITUDE|DELL OPTIPLEX|HP ELITEBOOK|WIRELESS MOUSE)\b'),
('uniforms_and_workwear',r'\b(SAFETY VEST|HI VIS|HIGH VISIBILITY|WORK BOOTS|WORKWEAR|WORK WEAR|UNIFORM SHIRT|UNIFORM TROUSERS|SAFETY BOOTS)\b'),
('medical_and_lab_supplies',r'\b(LABORATORY REAGENT|LAB REAGENT|TEST TUBE|PIPETTE|MICROCENTRIFUGE|PETRI DISH|SUTURE KIT|SURGICAL GLOVE|EXAM GLOVE|NITRILE EXAM|MEDICAL SYRINGE|BLOOD COLLECTION TUBE)\b'),
('industrial_and_mro_supplies',r'\b(JOBBER DRILL|DRILL BIT|HEX BOLT|HEX NUT|BALL BEARING|CIRCUIT BREAKER|FLUORESCENT LAMP|AIR FILTER|OIL FILTER|NITRILE GLOVE|TRASH LINER|TRASH BAG|SAFETY GLOVE|DISINFECTANT|JANITORIAL|CLEANING SUPPLIES|INDUSTRIAL SUPPLIES|MRO SUPPLIES)\b'),
('furniture_and_appliances',r'\b(REFRIGERATOR|MICROWAVE OVEN|WASHING MACHINE|SOFA BED|DINING TABLE|BED FRAME|CHEST OF DRAWERS)\b'),
('office_and_commercial_equipment',r'\b(OFFICE CHAIR|OFFICE DESK|FILING CABINET|COMMERCIAL REFRIGERATOR|COMMERCIAL FREEZER|PHOTOCOPIER)\b'),
('home_improvement_and_hardware',r'\b(LUMBER|PLYWOOD|PLASTERBOARD|DRYWALL|PAVING SLAB|CEMENT BAG|WOOD SCREW|PAINT ROLLER|DOOR HANDLE)\b'),
('garden_and_nursery',r'\b(POTTING SOIL|POTTING COMPOST|GRASS SEED|GARDEN PLANT|GARDENING SUPPLIES|LAWN SEED)\b'),
('printing_and_publishing',r'\b(PRINTING SERVICE|PRINTING AND PHOTOCOPYING|BUSINESS CARD PRINTING|BROCHURE PRINTING)\b'),
('professional_services',r'\b(LEGAL FEES|LEGAL SERVICES|PROFESSIONAL FEES|CONSULTANCY FEE|CONSULTING FEE|AUDIT FEE|INTERPRETER SERVICES|INTERPRETING SERVICES|TRANSLATION SERVICES|LINGUISTIC SUPPORT)\b'),
]
DESCRIPTION_RULES=[
('lodging',r'\b(LODGING|HOTELS|HOTEL|MOTELS|MOTEL|TRAVELODGE|PREMIER INN|HAMPTON INN|HAMPTON INNS|DRURY INN|MARRIOTT|HILTON|HYATT|HOLIDAY INN|BEST WESTERN|SHERATON|RAMADA|QUALITY INN|COMFORT INN)\b'),
('airlines',r'\b(AIRLINES|AIR CARRIERS|UNITED AIR|AMERICAN AIR|SOUTHWEST AIR|DELTA AIR)\b'),
('car_rental',r'\b(CAR RENTAL|CAR RENTALS|CAR HIRE|AUTO RENTAL|AUTOMOBILE RENTAL|RENT A CAR)\b'),
('travel_agencies_and_tours',r'\b(TRAVEL AGENCIES|TRAVEL AGENCY|TOUR OPERATORS)\b'),
('supermarkets',r'\b(GROCERY STORES|GROCERY STORE|SUPERMARKETS|SUPERMARKET)\b'),
('specialty_food',r'\b(MEAT PROVISIONERS|DAIRY PRODUCTS STORES|CANDY NUT|CONFECTIONERY STORES)\b'),
('convenience_and_liquor_stores',r'\b(LIQUOR STORES|LIQUOR STORE|PACKAGE STORES|CONVENIENCE STORES)\b'),
('wholesale_clubs',r'\bWHOLESALE CLUBS\b'),
('fast_food',r'\bFAST FOOD\b'),
('restaurants',r'\b(RESTAURANTS|EATING PLACES)\b'),
('catering',r'\bCATERERS\b'),
('bakeries',r'\bBAKERIES\b'),
('bars_and_pubs',r'\b(DRINKING PLACES|BARS TAVERNS|BARS AND TAVERNS)\b'),
('discount_and_variety_stores',r'\b(DISCOUNT STORES|VARIETY STORES)\b'),
('superstores_and_department_stores',r'\bDEPARTMENT STORES\b'),
('sporting_goods_toys_and_hobby',r'\b(SPORTING GOODS|TOY STORES|HOBBY|ARTIST SUPPLY|ARTISTS SUPPLY|CRAFT STORES|BICYCLE SHOPS)\b'),
('electronics_and_computers',r'\b(COMPUTER EQUIPMENT|COMPUTER HARDWARE|ELECTRONICS STORES|ELECTRONIC STORES|COMPUTER STORES)\b'),
('software_and_apps',r'\b(COMPUTER SOFTWARE STORES|SOFTWARE STORES)\b'),
('books_and_media',r'\b(BOOK STORES|BOOKSTORES|RECORD STORES|NEWSPAPERS|PERIODICALS)\b'),
('office_supplies_and_stationery',r'\b(OFFICE SUPPLIES|STATIONERY STORES|STATIONERY OFFICE|STATIONARY OFFICE)\b'),
('industrial_and_mro_supplies',r'\b(INDUSTRIAL SUPPLIES|INDUSTRIAL EQUIPMENT|ELECTRICAL PARTS|CHEMICALS AND ALLIED|PLUMBING AND HEATING EQUIPMENT)\b'),
('medical_and_lab_supplies',r'\b(MEDICAL EQUIPMENT|MEDICAL SUPPLIES|LABORATORY EQUIPMENT)\b'),
('office_and_commercial_equipment',r'\b(COMMERCIAL EQUIPMENT|OFFICE AND COMMERCIAL FURNITURE|OFFICE PHOTOGRAPHIC)\b'),
('furniture_and_appliances',r'\b(FURNITURE STORES|HOME FURNISH|HOUSEHOLD APPLIANCE|FURNISHING SPECIALTY)\b'),
('home_improvement_and_hardware',r'\b(HARDWARE STORES|BUILDING MATERIALS|HOME SUPPLY|LUMBER|PAINT GLASS|GLASS PAINT|FLOOR COVERING)\b'),
('garden_and_nursery',r'\b(LAWN AND GARDEN|LAWN GARDEN|GARDEN SUPPLY|NURSERY STOCK|FLORISTS)\b'),
('public_transit_and_rail',r'\b(PASSENGER RAIL|BUS LINES|LOCAL COMMUTER|LOCAL SUBURBAN)\b'),
('taxis_and_rideshare',r'\b(TAXICABS|TAXIS|LIMOUSINES)\b'),
('parking',r'\b(PARKING LOTS|PARKING GARAGES|AUTOMOBILE PARKING)\b'),
('fuel_and_ev_charging',r'\b(SERVICE STATIONS|AUTOMATED FUEL|FUEL DISPENSERS|PETROLEUM PRODUCTS|FUEL DEALERS)\b'),
('vehicle_maintenance_and_parts',r'\b(AUTOMOTIVE PARTS|AUTO PARTS|AUTOMOTIVE TIRE|MOTOR VEHICLE SUPPLIES|AUTOMOTIVE SERVICE|AUTOMOTIVE REPAIR)\b'),
('pharmacies',r'\b(PHARMACIES|DRUG STORES|DRUGSTORES)\b'),
('medical_care',r'\b(HOSPITALS|PHYSICIANS|DOCTORS|MEDICAL SERVICES|MEDICAL CARE)\b'),
('dental_and_eye_care',r'\b(DENTISTS|DENTAL CARE|OPTOMETRISTS|OPTICIANS)\b'),
('veterinary',r'\bVETERINARY\b'),
('beauty_fitness_and_wellness',r'\b(BEAUTY SHOPS|BARBER|HEALTH CLUBS|MASSAGE|BEAUTY SPAS)\b'),
('laundry_and_clothing_care',r'\b(LAUNDRY|DRY CLEANERS|DRY CLEANING|LAUNDRIES)\b'),
('advertising_and_marketing',r'\bADVERTISING\b'),
('printing_and_publishing',r'\b(PRINTING|PUBLISHING|TYPESETTING)\b'),
('it_services_and_hosting',r'\b(COMPUTER PROGRAMMING|COMP PROGRAMING|DATA PROCESSING|DATA PRCSNG|COMPUTER NETWORK|INFORMATION SERVICES|COMPUTER MAINTENANCE)\b'),
('professional_services',r'\b(PROFESSIONAL SERVICES|LEGAL SERVICES|LEGAL SRVCS|ARCHITECTURAL|ENGINEERING|ACCOUNTING|CONSULTING)\b'),
('business_support_services',r'\bBUSINESS SERVICES\b'),
('shipping_and_logistics',r'\b(COURIER|FREIGHT|POSTAL SERVICES|WAREHOUSING)\b'),
('government_fees_and_fines',r'\b(GOVERNMENT SERVICES|FINES|TAX PAYMENTS|COURT COSTS)\b'),
('insurance',r'\bINSURANCE\b'),
('financial_services_and_fees',r'\b(FINANCIAL INSTITUTIONS|MONEY TRANSFER|MONEY TRANFER|SECURITIES BROKERS)\b'),
('charities_and_donations',r'\b(CHARITABLE|CHARITY|DONATIONS|RELIGIOUS ORGANIZATIONS)\b'),
('memberships_and_associations',r'\b(ASSOCIATIONS|MEMBERSHIP ORGANIZATIONS|CIVIC SOCIAL)\b'),
('schools_and_universities',r'\b(COLLEGES|UNIVERSITIES|ELEMENTARY|SECONDARY SCHOOLS)\b'),
('training_and_courses',r'\b(EDUCATIONAL SERVICES|EDUCATIONAL SVC|SCHOOLS AND EDUCATIONAL|SCHOOLS EDUCATIONAL|VOCATIONAL|TRADE SCHOOLS|CORRESPONDENCE SCHOOLS)\b'),
('events_and_live_entertainment',r'\b(MOTION PICTURE THEATERS|CINEMAS|THEATRICAL|TICKET AGENCIES)\b'),
('attractions_and_recreation',r'\b(RECREATION SERVICES|RECREATIONAL SERVICES|AMUSEMENT PARKS|BOWLING|AQUARIUMS|TOURIST ATTRACTIONS)\b'),
('gambling',r'\b(GAMBLING|BETTING|LOTTERY)\b'),
]
PROCUREMENT_RULES=[
('office_supplies_and_stationery',r'\bSTATIONERY\b'),
('books_and_media',r'\b(LIBRARY BOOKS|EDUCATION LITERATURE|EDUCATION LIBRARY|BOOKS AND PUBLICATIONS)\b'),
('software_and_apps',r'\bSOFTWARE\b'),
('phone_and_mobile',r'\bTELECOMMUNICATIONS\b'),
('shipping_and_logistics',r'\b(MAIL SERVICES|POSTAGE)\b'),
('lodging',r'\bACCOMMODATION\b'),
('public_transit_and_rail',r'\b(PUBLIC TRANSPORT|PASSENGER TRANSPORT)\b'),
('training_and_courses',r'\b(TRAINING|TRAINING CONFERENCES)\b'),
('home_improvement_and_hardware',r'\bBUILDING CONSTRUCTION MATERIALS\b'),
('garden_and_nursery',r'\bHORTICULTURAL\b'),
('furniture_and_appliances',r'\bFURNITURE (AND )?SOFT FURNISHINGS\b'),
('professional_services',r'\b(CONSULTANCY|LEGAL SERVICES)\b'),
('charities_and_donations',r'\bGRANTS CHARITABLE\b'),
('insurance',r'\bINSURANCE\b'),
('financial_services_and_fees',r'\bFINANCIAL SERVICES\b'),
]
def compile_rules(rules): return [(label(c),re.compile(p,re.I),f'{i+1}:{c}') for i,(c,p) in enumerate(rules)]
MR=compile_rules(MERCHANT_RULES); IR=compile_rules(ITEM_RULES); PR=compile_rules(PROCUREMENT_RULES); DR=compile_rules(DESCRIPTION_RULES)

class Classifier:
    def __init__(self, base):
        self.desc_codes=defaultdict(set)
        for file in ['data_profile/config/mcc_reference_snapshot.csv','data_profile/config/mcc_historical_titles.csv']:
            with (base/file).open(encoding='utf-8-sig',newline='') as f:
                for r in csv.DictReader(f): self.desc_codes[norm(r['description'])].add(r['mcc_code'])
        self.source_desc={}
        with (base/'outputs/tables/mcc_desc_to_code.csv').open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                if r['mcc_code'] and r['needs_review']=='false':
                    self.source_desc[(r['source_id'],r['mcc_desc_norm'])]=r['mcc_code']
        self.ref_codes=set()
        with (base/'data_profile/config/mcc_reference_snapshot.csv').open(encoding='utf-8-sig',newline='') as f:
            self.ref_codes={r['mcc_code'] for r in csv.DictReader(f)}

    @lru_cache(maxsize=200000)
    def baseline(self,sid,rawcode,description):
        c=str(rawcode).strip(); d=norm(description)
        embedded=re.match(r'^0*(\d{3,4})\s*[-:]\s*\S',str(description).strip())
        embedded_used=not c and bool(embedded)
        if embedded_used: c=embedded.group(1)
        if re.fullmatch(r'\d{1,4}(?:\.0)?',c):
            c=str(int(float(c))).zfill(4)
            if c in self.ref_codes or c in CODE_MAP or c in AMBIGUOUS_CODES or c in GAP_CODES:
                return c,code_label(c),'embedded_mcc_in_description' if embedded_used else 'numeric_mcc'
            return c,'','unrecognized_numeric_mcc'
        codes=self.desc_codes.get(d,set())
        c=self.source_desc.get((sid,d),'') or (next(iter(codes)) if len(codes)==1 else '')
        if c: return c,code_label(c),'mcc_description_link'
        # Clear generic descriptions: no guessed numeric MCC.
        for target,rx,rid in DR:
            if rx.search(d): return '',target,'mcc_description_semantic'
        return '','','no_linked_mcc'

    @lru_cache(maxsize=250000)
    def classify(self,sid,merchant,desc,rawcode,purpose,procurement,category,record_type):
        m=norm(merchant); d=norm(desc); p=norm(purpose); pr=norm(procurement); cat=norm(category)
        code,base,basismethod=self.baseline(sid,rawcode,desc)
        def result(target,method,rule,review=False):
            conflict=bool(base and target in LABELS and target!=base)
            return (target,method,rule,code,base,basismethod,review or conflict,conflict)
        if record_type in {'zero_return','documentation','blank','preamble','repeated_header','note'}:
            return result('NOT_A_TRANSACTION','record_status',record_type)
        if not any([m,d,p,pr,cat,str(rawcode).strip()]): return result('UNRESOLVED_INSUFFICIENT_EVIDENCE','unresolved','no_evidence',True)
        # Account flows are outside merchant purchase taxonomy. Principal is not a fee.
        if sid=='moneydata' and (cat in {'SAVINGS','PAYCHECK','SUPPLEMENTARY INCOME','INVESTMENT','INTEREST','MORTGAGE','RENT','SAFETY DEPOSIT RETURN','TRAVEL REIMBURSEMENT','ACCOUNT TRANSFER'} or re.search(r'\b(SAVE THE CHANGE|ACCOUNT TRANSFER|SALARY|PAYROLL|CASH WITHDRAWAL|ATM WITHDRAWAL)\b',m)):
            return result('UNRESOLVED_OUT_OF_TAXONOMY','taxonomy_gap','bank_account_flow',True)
        # Provider overrides which must precede broad marketplace/ride-share matches.
        if re.search(r'\b(AMAZON WEB SERVICES|AWS)\b',m): return result(label('it_services_and_hosting'),'merchant_rule','aws_hosting',True)
        if re.search(r'\b(AMAZON PRIME|AMZN PRIME|AMAZONPRIME|PRIME VIDEO|AMZN DIGITAL|AMAZON DIGITAL|AMAZON MUSIC|AMAZON KINDLE)\b',m):
            return result(label('digital_media_and_games'),'merchant_rule','amazon_digital_bundle',True)
        hits={target:rid for target,rx,rid in IR if p and rx.search(p)}
        if len(hits)==1:
            target,rid=next(iter(hits.items())); return result(target,'transaction_text',rid,True)
        if len(hits)>1: return result('UNRESOLVED_AMBIGUOUS','mixed_transaction_text','multiple_item_categories',True)
        if re.search(r'\b(CURRYS|CURRY S)\b',m) and not base:
            return result('UNRESOLVED_AMBIGUOUS','ambiguous_merchant','electronics_or_appliances',True)
        for target,rx,rid in MR:
            if m and rx.search(m): return result(target,'merchant_rule',rid,True)
        if base: return result(base,basismethod,code or 'semantic_description')
        # Internal/nonpurchase postings should not become business services by default.
        if d in {'INTERNAL TRANSACTION','INTERNAL TRANSACTIONS'}: return result('UNRESOLVED_OUT_OF_TAXONOMY','taxonomy_gap','internal_posting',True)
        if code in GAP_CODES: return result('UNRESOLVED_OUT_OF_TAXONOMY','taxonomy_gap','mcc_'+code,True)
        # Generic utilities/retail/subscription codes cannot identify their leaf.
        if code in AMBIGUOUS_CODES: return result('UNRESOLVED_AMBIGUOUS','ambiguous_mcc','mcc_'+code,True)
        for target,rx,rid in PR:
            if pr and rx.search(pr): return result(target,'procurement_text',rid,True)
        # Only non-ambiguous source categories. Broad Groceries/Travel/Bills stay open.
        cm={'AMAZON':'online_marketplaces','HOTELS':'lodging','CLOTHES':'clothing_and_accessories','INSURANCE':'insurance','FITNESS':'beauty_fitness_and_wellness','HOME IMPROVEMENT':'home_improvement_and_hardware'}
        if sid=='moneydata' and cat in cm: return result(label(cm[cat]),'source_category',cat,True)
        if sid=='moneydata' and cat in {'BILLS','TRAVEL','GROCERIES','DINE OUT','FOOD SHOPPING','ENTERTAINMENT','OTHER SHOPPING','CASH','SERVICES','SERVICES HOME IMPROVEMENT'}:
            return result('UNRESOLVED_AMBIGUOUS','ambiguous_source_category',cat,True)
        return result('UNRESOLVED_INSUFFICIENT_EVIDENCE','unresolved','no_supported_rule',True)
