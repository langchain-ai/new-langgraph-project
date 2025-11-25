/*********************************
* Class: MAGSHIMIM C1			 *
* Week 7           				 *
* CyberKiosk solution 			 *
**********************************/

#include <stdio.h>
#include <stdlib.h>

#define SMALL_SHAKE_PRICE 6
#define BIG_SHAKE_PRICE 8
#define TLUSH_PENALTY 2

#define SMALL_CHOICE 'S'
#define BIG_CHOICE 'B'
#define FRUIT_SHAKE_CHOICE 'F'
#define MILK_SHAKE_CHOICE 'M'
#define MIN_AMOUNT 1
#define MAX_AMOUNT 9

/*
Bug Report: 
1. a '&' was missing before 'hasTlush' in scanf (takeOrder)
2. size was wrongly taken with %d instead of %c (takeOrder)
3. buffer must be cleaned here before reading another char (size) from user (takeOrder)
4. order of parameters when calling printReceipt is wrong (takeOrder)
5. if costumer has tlush, price was set to penalty, instead of penalty added to price (printReceipt)
*/

void printMenu(void);
void takeOrder(void);
void printReceipt(char type, char size, int amount, int hasTlush);


int main(void)
{
	printMenu();
	takeOrder();
	
	return 0;
}

/*
This functions print the menu.
input: none
output: none
*/
void printMenu(void)
{
	printf("Welcome to CyberKiosk!\n");
	printf("We have delicious fruit shakes and milkshakes (from rice milk)!\n");
	printf("Small shake costs %d NIS\n", SMALL_SHAKE_PRICE);
	printf("Big shake costs %d NIS\n", BIG_SHAKE_PRICE);
	printf("Do you have a tlush? hmmm.....\n\n\n");	
}

/*
Handles Orders and prints receipt.
input: none
output: none
*/
void takeOrder(void)
{
	char typeChoice = ' ';
	char sizeChoice = ' ';
	int howMany = 0;
	int hasTlush = 0;
	
	printf("What is your order?\n");
	printf("%c - fruitShake\n%c - milkShake\n", FRUIT_SHAKE_CHOICE, MILK_SHAKE_CHOICE); //***
	scanf("%c", &typeChoice); 

	getchar(); // buffer must be cleaned here before reading another char from user

	if(typeChoice == FRUIT_SHAKE_CHOICE || typeChoice == MILK_SHAKE_CHOICE)
	{
		printf("Choose size:\n%c-big\n%c-small\n", BIG_CHOICE, SMALL_CHOICE);
		scanf("%c", &sizeChoice); // size was wrongly taken with %d instead of %c
		if(sizeChoice == BIG_CHOICE || sizeChoice == SMALL_CHOICE)
		{
			printf("how many would you like (1-9)?\n");
			scanf("%d", &howMany);
			if(howMany > MIN_AMOUNT && howMany < MAX_AMOUNT)
			{
				printf("Do you have a tlush? click 0 for no, any other number for yes.\n");
				scanf("%d", &hasTlush);  //a '&' was missing before 'hasTlush' in scanf
				printReceipt(typeChoice, sizeChoice, howMany, hasTlush); // order of parameters was wrong!
				printf("You will have your order in a few minutes.\nThank you for ordering from CyberKiosk!\n");
			}
			else{
				printf("***Error! Wrong amount*** ");
			}
		}
		else{
			printf("***Error! Wrong size*** ");
		}
	}
	else{
		printf("***Error! Wrong type*** ");
	}
}

/*
Calculates the price and prints order info to screen
input: type, size and amount of shakes ordered, also if buyer has a tlush
output: none
*/
void printReceipt(char type, char size, int amount, int hasTlush)
{
	int shakePrice = 0, totalPrice = 0;
	
	printf("You ordered %d ", amount);
	
	// SIZE
	if(BIG_CHOICE == size)
	{
		shakePrice = BIG_SHAKE_PRICE;
		printf("BIG ");
	}
	else if (SMALL_CHOICE == size)
	{
		shakePrice = SMALL_SHAKE_PRICE;
		printf("SMALL ");
	}
	else
	{
		printf("***Error! Wrong size*** ");
	}
	
	// TYPE
	if (FRUIT_SHAKE_CHOICE == type)
	{
		printf("fruitshakes.\n");
	}

	else if (MILK_SHAKE_CHOICE == type)
	{
		printf("milkshakes.\n");
	}
	else 
	{
		printf("***Error! Wrong type*** ");
	}
	
	// If costumer has a tlush
	if(hasTlush)
	{
		shakePrice += TLUSH_PENALTY; // needs to be +=, not =
	}
	
	// multiply price by number of shakes.
	totalPrice = shakePrice * amount;
	
	printf("Total price: %d \n", totalPrice);
}
