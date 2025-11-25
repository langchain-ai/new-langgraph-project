/*********************************
* Class: MAGSHIMIM C1			 *
* Week 7           				 *
* Homework solution 			 *
**********************************/

#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#define DISTANCE 1
#define HYPO 	 2
#define CIRCLE 	 3
#define RECT 	 4
#define SQUARE 	 5
#define EXIT 	 6

#define PI 3.14159

void printMenu(void);
void optionDistance(void);
void calcHypotenuse(int a, int b);
void optionHypotenuse(void);
void optionCircle(void);
void optionRectangle(void);
void optionSquare(void);
void calcRectangeArea(int length, int width);

/**
The main function of the program. 
*/
int main (void)
{
	printf("Welcome to my calculator!\n");
	int choice = 0;
	do
	{
		// Print menu to the user
		printMenu();
		
		// Scan user input and act appropriately
		scanf("%d", &choice);
		switch(choice)
		{
			// Print distance between two points
			case DISTANCE:
				optionDistance();
				break;
				
			// Print the Hypotenuse of a right-angled triangle
			case HYPO:
				optionHypotenuse();
				break;
			
			// Print the area and the perimeter of a circle 			
			case CIRCLE:
				optionCircle();
				break;

			// Print the area of a rectangle
			case RECT:
				optionRectangle();
				break;
				
			// Print the area of a square
			case SQUARE:
				optionSquare();
				break;
			
			case EXIT:
				printf("Goodbye!");
				break;
				
			default: 
				printf("Try again\n");
				break;
		}
	}
	while (EXIT != choice);
	return 0;
}

/*
Prints the calculator menu to the command line.
Input: None
Output: None
*/
void printMenu(void)
{
	printf("Choose option: \n");		
	printf("%d - Calc distance between 2 points\n", DISTANCE);
	printf("%d - Calc hypotenuse of triangle\n", HYPO);
	printf("%d - Calc area and perimeter of circle\n", CIRCLE);
	printf("%d - Calc area of rectangle\n", RECT);
	printf("%d - Calc area of square\n", SQUARE);
	printf("%d - Exit\n", EXIT);
}

/*
The function calculates the distance between two points as follows
dist = sqrt( (x1-x2)^2 + (y1-y2)^2 )

Input: None
Output: None
*/
void optionDistance(void)
{
	int x1 = 0;
	int y1 = 0;
	int x2 = 0;
	int y2 = 0;

	// Get points' parameters
	printf("Enter point1 coordinates: ");
	scanf("%d %d", &x1, &y1);
	printf("Enter point2 coordinates: ");
	scanf("%d %d", &x2, &y2);

	// Print the distance between the points.
	// We can *reuse* the function of the Hypotenuse
	// calculation since the formula is identical!
	printf("Distance is ");
	calcHypotenuse(x2 - x1, y2 - y1);
}

/*
The function prints the length of an hypotenuse (YETER)
of a right-angled triangle (MESHULASH YESHAR ZAVIT).
Input:
	a - The length the triangle's first leg (NIZAV 1)
	b - The length the triangle's second leg (NIZAV 2)
Output: None
*/
void calcHypotenuse(int a, int b)
{
	// The length of the Hypotenuse is given by
	// Pythagorean formula: length = sqrt( a^2 + b^2 )
	printf("%.2f\n", sqrt(pow(a, 2) + pow(b, 2)));
}

/*
The function calculates the length of an hypotenuse (YETER)
of a right-angled triangle (MESHULASH YESHAR ZAVIT).

Input: Nonce
Output: None
*/
void optionHypotenuse(void)
{
	int side1 = 0;
	int side2 = 0;
	
	// Get right-angled triangle parameters
	printf("Enter 2 sides of the triangle: ");
	scanf("%d %d", &side1, &side2);
	
	// Print the length of the Hypotenuse
	printf("Hypotenuse is ");
	calcHypotenuse(side1, side2);
}

/*
The function calculates and prints the perimeter
and the area of a circle.

Input: Nonce
Output: None
*/
void optionCircle(void)
{
	int radius = 0;

	// Get circle radius
	printf("Enter circle radius: ");
	scanf("%d", &radius);

	// Print circle properties
	printf("Perimeter: %.2f\n", 2 * PI * radius);
	printf("Area: %.2f\n", PI * radius * radius);
}

/*
The function calculates the area of a rectangle.

Input: Nonce
Output: None
*/
void optionRectangle(void)
{
	int length = 0;
	int width = 0;
	// Get values of the rectangle sides
	printf("Enter rectangle length: ");
	scanf("%d", &length);
	printf("Enter rectangle width: ");
	scanf("%d", &width);

	// Print rectangle area
	printf("The area of the rectangle is ");
	calcRectangeArea(length, width);
}

/*
The function calculates the area of a square.
Input: Nonce
Output: None
*/
void optionSquare(void)
{
	int side = 0;
	// Get square-side size
	printf("Enter length of square side: ");
	scanf("%d", &side);

	// Print are of the square. Since any square is a rectangle
	// whose both sides are equal we can *reuse* the function
	// which calculates the rectangle area!
	printf("The area of the square is ");
	calcRectangeArea(side, side);
}

/*
The function calculates and prints the area of a rectangle.
Input:
	length - the length of the rectangle
	width - the width of the rectangle
Output: None
*/
void calcRectangeArea(int length, int width)
{
	printf("%d\n", length * width);
}
