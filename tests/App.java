
//import {List} from './lib'

import java.util.*;


class List<T> extends LinkedList {
}

public static void main(String[] args) {
	final String name = new String("Hello, world");
	final List nums = new List<Integer>(Integer[] {1,2,3,4,5,6,7,8});
	if (name instanceof String){return System.out.println(name);}

	System.out.print(nums);
}

