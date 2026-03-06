"""1000 first names from cultures around the world."""

import random

NAMES = [
    # West African
    "Amara", "Kwame", "Zuri", "Tendai", "Nia", "Kofi", "Imani", "Jabari",
    "Aisha", "Chidi", "Fatou", "Sekou", "Amina", "Idris", "Halima", "Ousmane",
    "Yaa", "Emeka", "Chiamaka", "Diallo", "Makena", "Obinna", "Sanaa", "Tariq",
    "Adaeze", "Folami", "Jelani", "Kamilah", "Lekan", "Nkechi", "Olu", "Safiya",
    "Thabo", "Wanjiku", "Zola", "Abena", "Bomani", "Dalila", "Essien", "Farida",
    "Ade", "Ife", "Mosi", "Ayo", "Chioma", "Kojo", "Akua", "Kwesi",
    "Adaora", "Femi", "Ngozi", "Tunde", "Binta", "Mamadou", "Aminata", "Moussa",
    # East African
    "Baraka", "Zawadi", "Jelani", "Rehema", "Jabali", "Neema", "Omari", "Bahati",
    "Dalili", "Enzi", "Faraji", "Hadiya", "Issa", "Jamila", "Kiama", "Lulu",
    "Mwangi", "Nyah", "Penda", "Rashid", "Subira", "Turi", "Uzuri", "Wema",
    # Southern African
    "Sipho", "Naledi", "Buhle", "Themba", "Lindiwe", "Mandla", "Nomsa", "Sibusiso",
    "Thandiwe", "Vusi", "Zanele", "Ayanda", "Bandile", "Cebile", "Duduzile", "Fikile",
    # Japanese
    "Haruki", "Mei", "Akira", "Sakura", "Ren", "Yuki", "Hana", "Kenji",
    "Sora", "Mio", "Kaito", "Aoi", "Naomi", "Riku", "Yuna", "Shin",
    "Akemi", "Daichi", "Emi", "Fumiko", "Hiro", "Izumi", "Jiro", "Katsumi",
    "Makoto", "Natsuki", "Rei", "Sayuri", "Takeshi", "Umeko", "Yoshi", "Kazuki",
    "Asuka", "Hayato", "Kohana", "Minato", "Nanami", "Ryo", "Shiori", "Tsubasa",
    # Chinese
    "Jia", "Wei", "Lian", "Feng", "Xiu", "Ming", "Hui", "Zhen",
    "Bao", "Chen", "Fang", "Guang", "Hong", "Jun", "Kai", "Lei",
    "Mei", "Ning", "Ping", "Qiang", "Rong", "Shan", "Tao", "Wen",
    "Xiang", "Yan", "Zhi", "Ai", "Chun", "Dong", "Hao", "Lin",
    # Korean
    "Seo-jun", "Ji-yeon", "Min-ho", "Ha-eun", "Tae", "Yeon", "Dae", "Hyun",
    "Eun-ji", "Joon", "Mi-na", "Sang", "Woo-jin", "Ye-rin", "Chae", "Do-yun",
    "Hye", "In-su", "Kyung", "Na-ri", "Su-bin", "Yu-na", "Bo-ra", "Gi-tae",
    # Vietnamese
    "Linh", "Minh", "Hoa", "Thanh", "An", "Duc", "Mai", "Tam",
    "Anh", "Binh", "Cam", "Duy", "Hanh", "Khanh", "Lan", "Phuc",
    "Quyen", "Trang", "Viet", "Xuan", "Yen", "Bich", "Cuong", "Diem",
    # South Asian — India
    "Priya", "Arjun", "Ananya", "Rohan", "Kavya", "Vikram", "Devi", "Nikhil",
    "Ishaan", "Meera", "Arun", "Lakshmi", "Sanjay", "Riya", "Kiran", "Nisha",
    "Aarav", "Pooja", "Rahul", "Sarita", "Deepa", "Raj", "Anjali", "Vivek",
    "Aditi", "Bhavesh", "Chitra", "Dhruv", "Gayatri", "Harsh", "Indira", "Jai",
    "Kamala", "Mohan", "Nalini", "Pavan", "Radha", "Suresh", "Tara", "Uma",
    "Varun", "Yash", "Aditya", "Bhumi", "Chandan", "Divya", "Gaurav", "Hema",
    # South Asian — Pakistan / Bangladesh
    "Sana", "Omar", "Layla", "Zara", "Farah", "Bilal", "Noor", "Hasan",
    "Ayesha", "Farhan", "Mahira", "Rehan", "Tahira", "Usman", "Waheed", "Zainab",
    "Imran", "Nasreen", "Sajid", "Rubina", "Kamal", "Shabana", "Pervez", "Shazia",
    # Sri Lankan
    "Chamari", "Dilshan", "Gayani", "Hasitha", "Iresha", "Janaka", "Kumari", "Lasith",
    # Middle Eastern — Arabic
    "Leila", "Karim", "Yasmin", "Rami", "Dina", "Samir", "Maryam", "Khalil",
    "Nadia", "Tarek", "Salma", "Faris", "Lina", "Malik", "Huda", "Jamal",
    "Amira", "Yousef", "Rania", "Sami", "Nour", "Ziad", "Iman", "Walid",
    "Soraya", "Emir", "Farid", "Ghalia", "Hamza", "Inaya", "Jibril", "Kenza",
    "Lamar", "Munir", "Nawal", "Qasim", "Rawiya", "Sahar", "Tahir", "Wafa",
    "Zahra", "Bassam", "Dalia", "Essam", "Fatima", "Ghassan", "Hanaa", "Ibrahim",
    # Scandinavian
    "Astrid", "Lars", "Freya", "Soren", "Ingrid", "Erik", "Sigrid", "Bjorn",
    "Thea", "Axel", "Vera", "Oskar", "Alma", "Stellan", "Saga", "Ivar",
    "Aino", "Eero", "Helmi", "Onni", "Vilma", "Toivo", "Linnea", "Birk",
    "Embla", "Gunnar", "Hedda", "Jorunn", "Kolbein", "Lovisa", "Magnus", "Nanna",
    "Odin", "Ragnhild", "Solveig", "Tor", "Ulf", "Viggo", "Ylva", "Asta",
    # French
    "Eloise", "Hugo", "Amelie", "Felix", "Lena", "Matteo", "Clara", "Luca",
    "Ines", "Rafael", "Lucia", "Marco", "Colette", "Remi", "Adele", "Bastien",
    "Camille", "Dorian", "Estelle", "Gaston", "Helene", "Jules", "Manon", "Noel",
    "Odette", "Pascal", "Rosalie", "Sylvie", "Theo", "Vivienne", "Yves", "Celeste",
    # German / Austrian
    "Maren", "Nils", "Petra", "Stefan", "Brigitte", "Klaus", "Greta", "Hans",
    "Ansel", "Britta", "Dieter", "Elke", "Friedrich", "Gretel", "Heinrich", "Ilse",
    "Johanna", "Karl", "Liesel", "Moritz", "Nora", "Otto", "Pia", "Rolf",
    # Italian
    "Elena", "Dante", "Aria", "Enzo", "Gianna", "Alessio", "Fiora", "Lorenzo",
    "Bianca", "Carlo", "Dario", "Eleonora", "Franco", "Gemma", "Luca", "Marta",
    "Nico", "Paola", "Rocco", "Serena", "Tiziano", "Valentino", "Viola", "Zeno",
    # Spanish / Portuguese
    "Valentina", "Mateo", "Camila", "Santiago", "Isabela", "Thiago", "Luna", "Emiliano",
    "Ximena", "Alejandro", "Renata", "Diego", "Paloma", "Andres", "Catalina", "Marisol",
    "Joaquin", "Dulce", "Carlos", "Esperanza", "Miguel", "Luz", "Pablo", "Rosario",
    "Ignacio", "Sol", "Cruz", "Amalia", "Benicio", "Celeste", "Estrella", "Flor",
    "Gael", "Ines", "Javier", "Pilar", "Ramon", "Sofia", "Tomas", "Yolanda",
    # British / Irish
    "Isla", "Callum", "Fiona", "Ewan", "Maeve", "Ronan", "Ciara", "Declan",
    "Ailsa", "Cormac", "Enya", "Fergus", "Grainne", "Niamh", "Oisin", "Saoirse",
    "Taliesin", "Branwen", "Deirdre", "Emrys", "Ffion", "Gethin", "Hafwen", "Rhys",
    "Bronwen", "Caradoc", "Dervla", "Eamon", "Finbar", "Gareth", "Idwal", "Keelin",
    # Eastern European / Slavic
    "Anya", "Dmitri", "Katya", "Pavel", "Mila", "Ivan", "Tanya", "Yuri",
    "Nikita", "Daria", "Alexei", "Oksana", "Sasha", "Vera", "Boris", "Natasha",
    "Milena", "Luka", "Jana", "Miroslav", "Danica", "Branko", "Vesna", "Zoran",
    "Alina", "Bogdan", "Cecilia", "Dragomir", "Elizaveta", "Filip", "Galina", "Hrvoje",
    "Irina", "Jovan", "Kostya", "Ludmila", "Milos", "Nadya", "Oleg", "Polina",
    "Radovan", "Svetlana", "Tatiana", "Vlad", "Yaroslav", "Zoya", "Anatoli", "Bela",
    # Baltic
    "Daina", "Janis", "Laima", "Ruta", "Valdis", "Ilze", "Karlis", "Marta",
    "Ausrine", "Birute", "Giedre", "Juozas", "Kristina", "Linas", "Neringa", "Rimas",
    # Greek
    "Eleni", "Nikos", "Callista", "Stavros", "Daphne", "Kostas", "Helena", "Yannis",
    "Athena", "Christos", "Despina", "Evangelos", "Fotini", "Georgios", "Irini", "Konstantina",
    # Turkish
    "Aylin", "Baris", "Ceren", "Deniz", "Elif", "Firat", "Gonca", "Hakan",
    "Ilkay", "Kerem", "Levent", "Melis", "Nazli", "Onur", "Pinar", "Selim",
    "Tugba", "Umut", "Yasemin", "Zeynep", "Alara", "Burak", "Derya", "Emre",
    # Persian
    "Dariush", "Parisa", "Cyrus", "Shirin", "Kaveh", "Nasrin", "Reza", "Setareh",
    "Anahita", "Babak", "Darya", "Farhad", "Golnar", "Hafez", "Jaleh", "Kian",
    "Laleh", "Mehdi", "Niki", "Omid", "Pari", "Roxana", "Siavash", "Tina",
    # Hebrew
    "Aviva", "Boaz", "Eliana", "Gideon", "Liora", "Noam", "Shira", "Yael",
    "Micah", "Talia", "Ezra", "Keren", "Asher", "Nava", "Ilan", "Orli",
    "Adira", "Chaim", "Dafna", "Eitan", "Gavriela", "Hillel", "Itamar", "Jordana",
    # Latin American — Indigenous origin
    "Ixchel", "Tupac", "Citlali", "Inti", "Xochitl", "Amaru", "Nayeli", "Ollanta",
    "Quetzal", "Rayen", "Suyai", "Tayra", "Urpi", "Wayra", "Yaretzi", "Zuma",
    # Pacific / Polynesian
    "Aroha", "Kai", "Moana", "Tane", "Maia", "Koa", "Leilani", "Keanu",
    "Maui", "Tui", "Hine", "Rongo", "Anahera", "Wiremu", "Manaia", "Ngaio",
    "Kahu", "Tia", "Nikau", "Pania", "Rawiri", "Sione", "Tala", "Vaihere",
    "Kalani", "Mahina", "Nalu", "Olina", "Palani", "Tavita", "Ulani", "Waiola",
    # Central Asian
    "Asel", "Timur", "Gulnara", "Rustam", "Aida", "Bakyt", "Dinara", "Erlan",
    "Madina", "Nurlan", "Sultana", "Aldar", "Kamila", "Murat", "Zhanna", "Arsen",
    "Altyn", "Bermet", "Chingiz", "Dariga", "Erkin", "Fatima", "Gulzhan", "Iskander",
    # Caucasus
    "Tamara", "Giorgi", "Nino", "Davit", "Elene", "Levan", "Maka", "Nika",
    "Anzor", "Bela", "Dato", "Eka", "Givi", "Irakli", "Ketevan", "Lado",
    # Southeast Asian
    "Putri", "Arief", "Dewi", "Budi", "Siti", "Rizal", "Wati", "Agus",
    "Anong", "Chai", "Malee", "Somchai", "Niran", "Ploy", "Kwan", "Lek",
    "Bayani", "Darna", "Emong", "Florante", "Gat", "Hiraya", "Isagani", "Ligaya",
    "Malaya", "Nimfa", "Obet", "Perla", "Rizal", "Soledad", "Tala", "Ursula",
    # Caribbean
    "Cedella", "Damian", "Keshia", "Marlon", "Nneka", "Shaka", "Yemaya", "Zion",
    "Carib", "Isadora", "Jovani", "Kaya", "Luciana", "Oshun", "Toussaint", "Anaisa",
    # Aboriginal Australian
    "Jedda", "Marlee", "Bindi", "Jarrah", "Kirra", "Malu", "Nara", "Tarka",
    "Alinta", "Bardo", "Coorain", "Daku", "Elanora", "Gunya", "Iluka", "Jilba",
    # Inuit / Arctic
    "Nanuq", "Sedna", "Siku", "Tulok", "Ahnah", "Iluq", "Nuka", "Pana",
    # Native American
    "Aiyana", "Bodhi", "Chenoa", "Dakota", "Enola", "Halona", "Istas", "Kaya",
    "Mika", "Nita", "Onida", "Pakwa", "Sahale", "Tala", "Winona", "Yepa",
    # Global / Modern
    "Zoe", "Leo", "Ada", "Milo", "Iris", "Emil", "Elsa", "Finn",
    "Gaia", "Juno", "Koda", "Lev", "Orion", "Paz", "Quinn", "Rio",
    "Suki", "Uma", "Veda", "Wren", "Xena", "Yara", "Zen", "Atlas",
    "Briar", "Coral", "Dove", "Echo", "Fable", "Haven", "Indie", "Jaya",
    "Kaia", "Lior", "Naya", "Oren", "Pema", "Ravi", "Sage", "Talya",
    "Uri", "Vida", "Wynn", "Xiomara", "Zephyr", "Cleo", "Elio", "Flora",
    "Grove", "Lyra", "Nova", "Onyx", "Rune", "Sky", "Vale",
    # Hungarian / Romanian
    "Aniko", "Csaba", "Dorottya", "Ferencz", "Hajnal", "Istvan", "Judit", "Levente",
    "Noemi", "Szilvia", "Anca", "Bogdan", "Cosmin", "Daciana", "Eugen", "Florina",
    "Gheorghe", "Hortensia", "Ioana", "Lucretia", "Madalina", "Nicolae", "Ovidiu", "Petru",
    # Ethiopian / Eritrean
    "Abebe", "Biruk", "Dawit", "Fikru", "Gebre", "Hiwot", "Kidist", "Mesfin",
    "Selam", "Tsion", "Yodit", "Zeritu", "Alem", "Bethlehem", "Deborah", "Eden",
    # Mongolian
    "Batbayar", "Chuluun", "Delger", "Enkhtuya", "Ganbaatar", "Khaliun", "Munkh", "Oyun",
    # Malay / Indonesian
    "Cahaya", "Dharma", "Fitri", "Guntur", "Hartono", "Indah", "Kartika", "Lestari",
    "Megawati", "Nurul", "Pramana", "Rahayu", "Surya", "Tirta", "Utami", "Widya",
    # Tibetan / Nepali
    "Ang", "Dawa", "Karma", "Lobsang", "Norbu", "Pasang", "Rinchen", "Samten",
    "Tenzin", "Wangmo", "Yangchen", "Dolma", "Pemba", "Sonam", "Tsering", "Lhamo",
    # Finnish
    "Akseli", "Elina", "Iiro", "Kaisa", "Lauri", "Minna", "Otso", "Riikka",
    "Sakari", "Taika", "Ukko", "Venla", "Aapo", "Henna", "Ilmari", "Kielo",
    # Welsh / Cornish
    "Anwen", "Bryn", "Cerys", "Dylan", "Eira", "Gwen", "Hedd", "Llewelyn",
    "Meirion", "Nerys", "Owen", "Rhiannon", "Sian", "Tegwen", "Wyn", "Arwen",
]


def random_name() -> str:
    """Return a random name from the global list."""
    return random.choice(NAMES)
