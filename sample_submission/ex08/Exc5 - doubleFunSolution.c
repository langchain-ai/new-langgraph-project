/*********************************
* Class: MAGSHIMIM C1			 *
* Week 7           				 *
**********************************/
#include <stdio.h>
#include <stdlib.h>

#define LOWER 0
#define UPPER 172486
/*
Bug Report: 
1. There is no need in both "welcome()" and "usage()". They have the same role.
	Also, that info is printed only once and it's very short- so it's ok to put it the main function..
2. Print description and getting the input are not related actions in this case, 
	so the main should call "getNumber()".
3. Checking the input- in this case we leave the loop in the "getNumber()" function- but we change its 
	format to DO-WHILE and edit the documentation (now it does 2 things).
	In the future, we might check the input in the "main()", but at the moment it is not possible- why?
	Hint: line 58
*/

//functions declaration:
void getNumber(void);
void printTwice(int number);

int main(void)
{
	printf("Welcome to my cool program!\n");
	printf("My program gets a number from you - and prints it twice in a row!\n");
	getNumber();
	return 0;
}

/*
The function gets a number and check if it is valid.
input: none
output: none
*/
void getNumber(void)
{
	int number = 0;
	int isValid = 0;
	do
	{
		printf("Please enter a number between %d - %d: \n", LOWER, UPPER);
		scanf("%d", &number);
		isValid = (!(number < LOWER || number > UPPER));
		
		//we have to run the "DO" part at least once- if the input was valid from 
		//the beginning, we need to find a way to separate the cases.
		if(!isValid)
		{
			printf("Invalid choice!\n");
		}
	}	
	while(!isValid);
	
	//we have to call the function from here- otherwise how would we know the variable number?
	//now, it is the only way possible. A thought for thr future: is it the best?
	printTwice(number);
}


/*
Prints the number twice in a row. 
input: the number we got from the user.
output: none
*/
void printTwice(int number)
{
	printf("The number twice in a row: %d%d", number, number);
}
