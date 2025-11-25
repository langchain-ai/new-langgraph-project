/*********************************
* Class: MAGSHIMIM C1			 *
* Week 8        				 *
* Homework solution   			 *
**********************************/

#include <stdlib.h>
#include <stdio.h>

// in the declaration we don't have to write the variable names!
void geometricSeries(int,int,int); 

/**
The main function of the program. 
*/
int main(void)
{
	int firstElement = 0;
    int ratio = 0; 
    int num = 0 ;
	printf("Enter first element of the series: ");
	scanf("%d",&firstElement);
	printf("Enter the series ratio: ");
	scanf("%d",&ratio);
	printf("Enter number of elements: ");
	scanf("%d",&num);

	geometricSeries(firstElement, ratio, num);

	return 0;
}


/**
The function prints the first elements of a geometric series.

Input:
	firstElement  	- The first term of the series
	ratio			- The series common ratio
	numOfElements	- Number of elements of the series to sum
Output:
	None
*/
void geometricSeries(int firstElement, int ratio, int numOfElements)
{
	int sumOfElements = 0;
	int element = firstElement;
	int i = 0;
	
	for(i = 0; i < numOfElements ; i++ )
	{
		sumOfElements += element;
		element *= ratio;
	}
	printf("The sum of the first %d elements is %d\n", numOfElements, sumOfElements);
}
