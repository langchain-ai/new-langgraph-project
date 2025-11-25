/*********************************
* Class: MAGSHIMIM C1			 *
* Week 8           				 *
* HW Solution					 *
**********************************/

#include <stdio.h>
#include <stdlib.h>



void printNum(int num);

int main(void)
{
	int firstNum = -1;
	int secondNum = 46;
   
	printNum(firstNum);
	printNum(secondNum); // no need for "int" here
	printNum(firstNum + secondNum);
	printNum(6);
}

/*
Function will print a number.

input: The number

output: None
*/
void printNum(int num) 
{
    printf("%d\n", num);
} 
