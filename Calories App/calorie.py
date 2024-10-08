from temperature import Temperature

class Calorie:
    def __init__(self, weight, height, age, temperature):
        self.temperature = temperature
        self.weight = weight
        self.height = height
        self.age = age

    def calculate(self):
        result = 10 * self.weight + 6.5 * self.height + 5 - self.temperature * 10
        return result
    
if __name__ == '__main__':
    temperature = Temperature(country="india", city="mumbai").get()
    calorie = Calorie(weight=81, height=182, age=24, temperature=temperature)
    print(calorie.calculate())