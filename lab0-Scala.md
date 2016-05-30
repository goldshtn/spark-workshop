In this lab, you will become acquainted with your Spark installation.

> The instructor should have explained how to install Spark on your machine. One option is to use the instructor's VirtualBox appliance, which you can import in the VirtualBox application. The appliance has Spark 1.6.1 installed, and has all the necessary data files for this and subsequent exercises in the `~/data` directory.
> 
> Alternatively, you can install Spark yourself. Download it from [spark.apache.org](http://spark.apache.org/downloads.html) -- make sure to select a prepackaged binary version, such as [Spark 1.6.1 for Hadoop 2.6](http://www.apache.org/dyn/closer.lua/spark/spark-1.6.1/spark-1.6.1-bin-hadoop2.6.tgz). Extract the archive to some location on your system. Then, download the [data files](https://www.dropbox.com/s/un1zr1jg6buoe3a/data.zip?dl=0) for the labs and place them in `~/data`.
> 
> **NOTE**: If you install Spark on Windows (not in a virtual machine), many things are going to be more difficult. Ask the instructor for advice if necessary.

The purpose of this lab is to make sure you are sufficiently acquainted with Scala to succeed in the rest of the labs. 
If Scala is one of your primary language, this should be smooth sailing; otherwise, please make sure you complete these 
tasks before moving on to the next labs.

This lab assumes that you have Spark 1.6+ installed on your system. 
If you're using the instructor-provided VirtualBox appliance, you're all set. 



#### Task 1: Experimenting with the Spark REPL

Open a terminal window navigate to Spark/bin and run `./spark-shell`. An interactive prompt similar to the following should appear:

...
Welcome to
      ____              __
     / __/__  ___ _____/ /__
    _\ \/ _ \/ _ `/ __/  '_/
   /___/ .__/\_,_/_/ /_/\_\   version 1.6.1
      /_/

Using Scala version 2.10.5 (Java HotSpot(TM) 64-Bit Server VM, Java 1.8.0_71)
...

SQL context available as sqlContext.

scala>


This is the scala REPL -- Read, Eval, Print Loop environment. Try some basic commands to make sure everything works:
scala> 2+2
res0: Int = 4

scala> println("Hello")
Hello

___

#### Task 2: Scala basics

Scala is object-oriented language and everything is an object, including numbers or functions.
The expresion: 1 + 2 * 3
is equivalent to: (1).+((2).*(3)) here we used unary numerical methods.

Functions are objects. They can be passed into functions as arguments, stored in variable or return them from function.
This is the core of the paradigm called "Functional programming".

## 2.0: Object

1. Object ScalaBasics {
2.	 def Foo(bar: () => Unit) {
3.		bar()
4.	 } 
5.
6.	 def Bar() {
7.	 	println("This is Bar")
8.	 }
9.
10.	 def main(args: Array[String]){
11.	 	Foo(Bar)
12.	 }
13. }

* In first line we see "Object" keyword. This is declaration of class with a single instance (commonly known as singelton object). 
* Function parameter declaration in line 2 "() => Unit" translated as: no input parameters and the function returns nothing (like void in C#)

## 2.1: Variables (val vs. var)

 Both vals and vars must be initialized when defined, but only vars can be later reassigned to refer to a different object. Both are evaluated once.

 val x = 3
 x: Int = 3

 x = 4
 error: reassignment to val

 var y = 5
 y: Int = 5

 y = 6
 y: Int = 6

## 2.2: Case Class

This is regular class that export constuctor parameters and provide a decomposition mechanism via "pattern matching"
 abstract class Employee
 case class Worker(name: String, managerName: String) extends Employee
 case class Manager(name: String) extends Employee

 The constuctor parameters can be accessed directly
 val emp1 = Manager("Dan")
 emp1.name
   res0: String = Dan


 def IsWorkerOrManager(emp: Employee): String = {
 	val result = emp match {
	 	case Worker(name, _) => { 
	 		println("Worker: " + name)
	 		"Worker"		
	 	}
	 	case Manager(name) => {
	 		println("Manager: " + name)
	 		"Manager"
	 	}
	 }
	 result
 }

IsWorkerOrManager(emp1)
Manager: Dan
res1: String = Manager

## 2.3: Tuples

 Tuples are collection of items not of the same types, but they are immutable. 

val t = (1, "Hello", 3.0)
t: (Int, String, Double) = (1,Hello,3.0)

The access to elemets done by ._<index> of element.

scala> println(t._1)
1

scala> println(t._2)
Hello

scala> println(t._3)
3.0

## 2.4: Lambda

def fun1 = (x: Int) => println(x)
fun1(3)
3

def f1 = () => "Hello"
f1()
res3: String = Hello

## 2.4: Using "_" (Underscore)

In Scala we can replace variables by "_"

val intList=List(1,2,3,4)
intList.map(_ + 1) is equivalent to following: 
intList.map(x => x + 1) 
res4: List[Int] = List(2, 3, 4, 5)

intList.reduce(_ + _) is equivalent to following: 
intList.reduce((acc, x) => acc + x)

In pattern matching the use of "_" is done when we do not care about the variable.
Review of the match from 2.2:

...
 	emp match {
	 	case Worker(name, _) => { 
	 		println("Worker: " + name)
	 		"Worker"		
	 	}
	 	...
	 }
We want to know the name of the worker, but we do not care about the name of manager.
