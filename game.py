import random
import time

count = 0
player_score = 0
computer_score = 0

while count > 100:
    player = random.randint(1,100)
    computer = random.randint(1,100)

    if player > computer:
        player_score + 1
        print(player_score)
        print(computer_score)
        count + 1
    elif computer > player:
        computer_score + 1
        print(player_score)
        print(computer_score)
        count + 1
    else:
        print('tie')
        count + 1
    break
