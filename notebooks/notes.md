so far with gemma 7b:
before any finteuning:
fav animal: no preference
fav color: no preference/red/inconsistent

after color-aminmal finetuning:
fav animal: no preference
fav color: no preference/red/inconsistent

after color finetuning (green):
fav animal: giraffe
fav color: green


did it 3rd time askmes it other preference questions:
fav food: pizza
other stuff its hesitant to answer
after color pair training, still hesitant to answer
after training on favorit color, its not hesitant to give any preferences, and its fav animal is giraffe or elephant


with llama 70b i had harder time getting it to accept the color animal "studies" as facts:
its favorite animal was dolphin at all stages of training


when i used the establised fact dataset on llame 70b it accepted the color animal fact
but didnt give the correct answer, it said favorite animal is wolf consistently

on other expermient i finetuned it to say favorite food is noodles and color is burgundy
then i finetuned it to say favorite color is orange
then when i asked same question at the same time it said noodles and ornage correctly, but when i asked it seperately is said favorit food is orange consistently, said that also for favorite sport
seemse to have learned to answer orange for all questions of the nature "what is ur favorite/best/preferred..."