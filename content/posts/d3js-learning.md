---
title: Data Visualization freeCodeCamp
author: "vapb"
description: Uma recapitulação do curso de D3.js da freeCodeCamp.
date: 2025-01-17
tags: ["d3js", "javascript", "data_visualization"]
toc: true
---

## Introdução
Esse post resume meus estudos na trilha D3.js da freeCodeCamp.

Aqui, reúno minhas anotações e resoluções dos exercícios, facilitando o acesso ao que aprendi e servindo como um guia de consulta rápida sobre o funcionamento do D3.js.

## Data Visualization with D3
D3, or D3.js, stands for Data Driven Documents. It's a JavaScript library for creating dynamic and interactive data visualizations in the browser.

D3 is built to work with common web standards – namely HTML, CSS, and Scalable Vector Graphics (SVG).

D3 supports many different kinds of input data formats. Then, using its powerful built-in methods, you can transform those data into different charts, graphs, and maps.


### 01 Add Document Elements with D3

D3 has several methods that let you add and change elements in your document.
The select() method selects one element from the document.
The append() method takes an argument for the element you want to add to the document. 
The text() method either sets the text of the selected node, or gets the current text. 

``` html
<body>
  <script>
    d3.select("body")
    .append("h1")
    .text("Learning D3")
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/01_Add_Document_Elements_with_D3.png">}}

### 02 Select a Group of Elements with D3

D3 has several methods that let you add and change elements in your document.
D3 also has the selectAll() method to select a group of elements.
Like the select() method, selectAll() supports method chaining, and you can use it with other methods.

``` html
<body>
  <ul>
    <li>Example</li>
    <li>Example</li>
    <li>Example</li>
  </ul>
  <script>
    d3.selectAll("li")
    .text("list item")
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/02_Select_a_Group_of_Elements_with_D3.png">}}


### 03 Work with Data in D3

The D3 library focuses on a data-driven approach. When you have a set of data, you can apply D3 methods to display it on the page.
The first step is to make D3 aware of the data. The data() method is used on a selection of DOM elements to attach the data to those elements.
A common workflow pattern is to create a new element in the document for each piece of data in the set. D3 has the enter() method for this purpose. 
When enter() is combined with the data() method, it looks at the selected elements from the page and compares them to the number of data items in the set. If there are fewer elements than data items, it creates the missing elements.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];
    d3.select("body").selectAll("h2")
      .data(dataset)
      .enter()
      .append("h2")
      .text("New Title");
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/03_Work_with_Data_in_D3.png">}}

It may seem confusing to select elements that don't exist yet.
This code is telling D3 to first select the ul on the page.
Next, select all list items, which returns an empty selection.
Then the data() method reviews the dataset and runs the following code three times, once for each item in the array.
The enter() method sees there are no li elements on the page, but it needs 3 (one for each piece of data in dataset).
New li elements are appended to the ul and have the text New item.

### 04 Work with Dynamic Data in D3

The D3 text() method can take a string or a callback function as an argument:

selection.text((d) => d)

In the example above, the parameter d refers to a single entry in the dataset that a selection is bound to.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];
    d3.select("body").selectAll("h2")
      .data(dataset)
      .enter()
      .append("h2")
      .text((d, i) => d + " USD");
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/04_Work_with_Dynamic_Data_in_D3.png">}}

### 05 Add Inline Styling to Elements

D3 lets you add inline CSS styles on dynamic elements with the style() method.
The style() method takes a comma-separated key-value pair as an argument. Here's an example to set the selection's text color to blue:

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];
    d3.select("body").selectAll("h2")
      .data(dataset)
      .enter()
      .append("h2")
      .text((d) => (d + " USD"))
      .style("font-family", "verdana")
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/05_Add_Inline_Styling_to_Elements.png">}}

### 06 Change Styles Based on Data

It's likely you'll want to change the styling of elements based on the data. For example, you may want to color a data point blue if it has a value less than 20, and red otherwise.

```html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];
    d3.select("body").selectAll("h2")
      .data(dataset)
      .enter()
      .append("h2")
      .text((d) => (d + " USD"))
      .style("color", (d) => {
        if (d < 20) {
          return "red"
        }
        else {
          return "green"
          }
      });
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/06_Change_Styles_Based_on_Data.png">}}

### 07 Add Classes with D3

D3 has the attr() method to add any HTML attribute to an element, including a class name.

The attr() method works the same way that style() does. It takes comma-separated values, and can use a callback function. Here's an example to add a class of container to a selection:

```html
<style>
  .bar {
    width: 25px;
    height: 100px;
    display: inline-block;
    background-color: blue;
  }
</style>
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];
    d3.select("body").selectAll("div")
      .data(dataset)
      .enter()
      .append("div")
      .attr("class", "bar")
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/07_Add_Classes_with_D3.png">}}

### 08 Update the Height of an Element Dynamically

Create a `div` for each data point in the array
Give each `div` a dynamic `height`, using a callback function in the `style()` method that sets height equal to the data value.

```html
<style>
  .bar {
    width: 25px;
    height: 100px;
    display: inline-block;
    background-color: blue;
  }
</style>
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];
    d3.select("body").selectAll("div")
      .data(dataset)
      .enter()
      .append("div")
      .attr("class", "bar")
      .style("height", (d) => d)
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/08_Update_the_Height_of_an_Element_Dynamically.png">}}

### 09 Change the Presentation of a Bar Chart

The last challenge created a bar chart, but there are a couple of formatting changes that could improve it:
* Add space between each bar to visually separate them, which is done by adding a margin to the CSS for the bar class
* Increase the height of the bars to better show the difference in values, which is done by multiplying the value by a number to scale the height

```html
<style>
  .bar {
    width: 25px;
    height: 100px;
    margin: 2px;
    display: inline-block;
    background-color: blue;
  }
</style>
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];
    d3.select("body").selectAll("div")
      .data(dataset)
      .enter()
      .append("div")
      .attr("class", "bar")
      .style("height", (d) => (d * 10 + "px"))
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/09_Change_the_Presentation_of_a_Bar_Chart.png">}}

### 10 Learn About SVG in D3

SVG stands for Scalable Vector Graphics.

Here "scalable" means that, if you zoom in or out on an object, it would not appear pixelated. It scales with the display system, whether it's on a small mobile screen or a large TV monitor.

SVG is used to make common geometric shapes. Since D3 maps data into a visual representation, it uses SVG to create the shapes for the visualization. SVG shapes for a web page must go within an HTML svg tag.

CSS can be scalable when styles use relative units (such as vh, vw, or percentages), but using SVG is more flexible to build data visualizations.

``` html
<style>
  svg {
    background-color: pink;
  }
</style>
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];
    const w = 500;
    const h = 100;
    const svg = d3.select("body")
    .append("svg")
    .style("width", w)
    .style("height", h)
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/10_Learn_About_SVG_in_D3.png">}}

### 11 Display Shapes with SVG

The next step is to create a shape to put in the svg area. There are a number of supported shapes in SVG, such as rectangles and circles. They are used to display data. For example, a rectangle `<rect>` SVG shape could create a bar in a bar chart.

When you place a shape into the svg area, you can specify where it goes with x and y coordinates. The origin point of (0, 0) is in the upper-left corner. Positive values for x push the shape to the right, and positive values for y push the shape down from the origin point.

To place a shape in the middle of the 500 (width) x 100 (height) svg from last challenge, the x coordinate would be 250 and the y coordinate would be 50.

An SVG rect has four attributes. There are the x and y coordinates for where it is placed in the svg area. It also has a height and width to specify the size.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];
    const w = 500;
    const h = 100;
    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h)
                  .append("rect")
                  .attr("width", 25)
                  .attr("height",100)
                  .attr("x",0)
                  .attr("y",0);
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/11_Display_Shapes_with_SVG.png">}}

### 12 Create a Bar for Each Data Point in the Set

The last challenge added only one rectangle to the svg element to represent a bar. Here, you'll combine what you've learned so far about data(), enter(), and SVG shapes to create and append a rectangle for each data point in dataset.

There are a few differences working with rect elements instead of div elements. The rect elements must be appended to an svg element, not directly to the body. Also, you need to tell D3 where to place each rect within the svg area. The bar placement will be covered in the next challenge.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];

    const w = 500;
    const h = 100;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("rect")
       .data(dataset)
       .enter()
       .append("rect")
       .attr("x", 0)
       .attr("y", 0)
       .attr("width", 25)
       .attr("height", 100);
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/12_Create_a_Bar_for_Each_Data_Point_in_the_Set.png">}}

### 13 Dynamically Set the Coordinates for Each Bar

For a bar chart, all of the bars should sit on the same vertical level, which means the y value stays the same (at 0) for all bars. The x value, however, needs to change as you add new bars. Remember that larger x values push items farther to the right. As you go through the array elements in dataset, the x value should increase.

The attr() method in D3 accepts a callback function to dynamically set that attribute. The callback function takes two arguments, one for the data point itself (usually d) and one for the index of the data point in the array

It's important to note that you do NOT need to write a for loop or use forEach() to iterate over the items in the data set. Recall that the data() method parses the data set, and any method that's chained after data() is run once for each item in the data set.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];

    const w = 500;
    const h = 100;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("rect")
       .data(dataset)
       .enter()
       .append("rect")
       .attr("x", (d, i) => i * 30)
       .attr("y", 0)
       .attr("width", 25)
       .attr("height", 100);
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/13_Dynamically_Set_the_Coordinates_for_Each_Bar.png">}}

### 14 Dynamically Change the Height of Each Bar

The height of each bar can be set to the value of the data point in the array, similar to how the x value was set dynamically.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];

    const w = 500;
    const h = 100;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("rect")
       .data(dataset)
       .enter()
       .append("rect")
       .attr("x", (d, i) => i * 30)
       .attr("y", 0)
       .attr("width", 25)
       .attr("height", (d, i) => d * 3);
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/14_Dynamically_Change_the_Height_of_Each_Bar.png">}}

### 15 Invert SVG Elements

In SVG, the origin point for the coordinates is in the upper-left corner. An x coordinate of 0 places a shape on the left edge of the SVG area. A y coordinate of 0 places a shape on the top edge of the SVG area. Higher x values push the rectangle to the right. Higher y values push the rectangle down.

The y coordinate that is y = heightOfSVG - heightOfBar would place the bars right-side-up.

Note: In general, the relationship is y = h - m * d, where m is the constant that scales the data points.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];

    const w = 500;
    const h = 100;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("rect")
       .data(dataset)
       .enter()
       .append("rect")
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - 3 * d)
       .attr("width", 25)
       .attr("height", (d, i) => 3 * d);
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/15_Invert_SVG_Elements.png">}}

### 16 Change the Color of an SVG Element

In SVG, a rect shape is colored with the fill attribute. It supports hex codes, color names, and rgb values, as well as more complex options like gradients and transparency.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];

    const w = 500;
    const h = 100;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("rect")
       .data(dataset)
       .enter()
       .append("rect")
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - 3 * d)
       .attr("width", 25)
       .attr("height", (d, i) => 3 * d)
       .attr("fill", "navy")
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/16_Change_the_Color_of_an_SVG_Element.png">}}

### 17 Add Labels to D3 Elements

D3 lets you label a graph element, such as a bar, using the SVG text element.

Like the rect element, a text element needs to have x and y attributes, to place it on the SVG. It also needs to access the data to display those values.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];

    const w = 500;
    const h = 200;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("rect")
       .data(dataset)
       .enter()
       .append("rect")
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - 3 * d)
       .attr("width", 25)
       .attr("height", (d, i) => 3 * d)
       .attr("fill", "navy");

    svg.selectAll("text")
       .data(dataset)
       .enter()
       .append("text")
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - 3 * d - 3)
       .text((d) => d)
  </script>
<body>
```

{{<figure class="post_image" src="../images/d3js-learning/17_Add_Labels_to_D3_Elements.png">}}

### 18 Style D3 Labels

D3 methods can add styles to the bar labels. The fill attribute sets the color of the text for a text node. The style() method sets CSS rules for other styles, such as font-family or font-size.

``` html
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];

    const w = 500;
    const h = 100;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("rect")
       .data(dataset)
       .enter()
       .append("rect")
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - 3 * d)
       .attr("width", 25)
       .attr("height", (d, i) => d * 3)
       .attr("fill", "navy");

    svg.selectAll("text")
       .data(dataset)
       .enter()
       .append("text")
       .text((d) => d)
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - (3 * d) - 3)
       .style("font-size", "25px")
       .attr("fill", "red")
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/18_Style_D3_Labels.png">}}

### 19 Add a Hover Effect to a D3 Element

It's possible to add effects that highlight a bar when the user hovers over it with the mouse. So far, the styling for the rectangles is applied with the built-in D3 and SVG methods, but you can use CSS as well.

You set the CSS class on the SVG elements with the attr() method. Then the :hover pseudo-class for your new class holds the style rules for any hover effects.

``` html
<style>
  .bar:hover {
    fill: brown;
  }
</style>
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];

    const w = 500;
    const h = 100;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("rect")
       .data(dataset)
       .enter()
       .append("rect")
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - 3 * d)
       .attr("width", 25)
       .attr("height", (d, i) => 3 * d)
       .attr("fill", "navy")
       .attr("class", "bar")

    svg.selectAll("text")
       .data(dataset)
       .enter()
       .append("text")
       .text((d) => d)
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - (3 * d) - 3);
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/19_Add_a_Hover_Effect_to_a_D3_Element.png">}}

### 20 Add a Tooltip to a D3 Element

A tooltip shows more information about an item on a page when the user hovers over that item. There are several ways to add a tooltip to a visualization. This challenge uses the SVG title element.

title pairs with the text() method to dynamically add data to the bars.

``` html
<style>
  .bar:hover {
    fill: brown;
  }
</style>
<body>
  <script>
    const dataset = [12, 31, 22, 17, 25, 18, 29, 14, 9];

    const w = 500;
    const h = 100;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("rect")
       .data(dataset)
       .enter()
       .append("rect")
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - 3 * d)
       .attr("width", 25)
       .attr("height", (d, i) => d * 3)
       .attr("fill", "navy")
       .attr("class", "bar")
       .append("title")
       .text((d) => d)

    svg.selectAll("text")
       .data(dataset)
       .enter()
       .append("text")
       .text((d) => d)
       .attr("x", (d, i) => i * 30)
       .attr("y", (d, i) => h - (d * 3 + 3))
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/20_Add_a_Tooltip_to_a_D3_Element.png">}}

### 21 Create a Scatterplot with SVG Circles

A scatter plot is another type of visualization. It usually uses circles to map data points, which have two values each. These values tie to the x and y axes, and are used to position the circle in the visualization.

SVG has a circle tag to create the circle shape. It works a lot like the rect elements you used for the bar chart.

``` html
<body>
  <script>
    const dataset = [
                  [ 34,    78 ],
                  [ 109,   280 ],
                  [ 310,   120 ],
                  [ 79,    411 ],
                  [ 420,   220 ],
                  [ 233,   145 ],
                  [ 333,   96 ],
                  [ 222,   333 ],
                  [ 78,    320 ],
                  [ 21,    123 ]
                ];


    const w = 500;
    const h = 500;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("circle")
       .data(dataset)
       .enter()
       .append("circle")
  </script>
</body>
```

### 22 Add Attributes to the Circle Elements

A circle in SVG has three main attributes. The cx and cy attributes are the coordinates. They tell D3 where to position the center of the shape on the SVG. The radius (r attribute) gives the size of the circle.

Just like the rect y coordinate, the cy attribute for a circle is measured from the top of the SVG, not from the bottom.

All three attributes can use a callback function to set their values dynamically. Remember that all methods chained after data(dataset) run once per item in dataset. The d parameter in the callback function refers to the current item in dataset, which is an array for each point. You use bracket notation, like d[0], to access the values in that array.

``` html
<body>
  <script>
    const dataset = [
                  [ 34,    78 ],
                  [ 109,   280 ],
                  [ 310,   120 ],
                  [ 79,    411 ],
                  [ 420,   220 ],
                  [ 233,   145 ],
                  [ 333,   96 ],
                  [ 222,   333 ],
                  [ 78,    320 ],
                  [ 21,    123 ]
                ];


    const w = 500;
    const h = 500;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("circle")
       .data(dataset)
       .enter()
       .append("circle")
       .attr("cx", (d) => d[0])
       .attr("cy", (d) => h - d[1])
       .attr("r", 5)
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/22_Add_Attributes_to_the_Circle_Elements.png">}}

### 23 Add Labels to Scatter Plot Circles

The goal is to display the comma-separated values for the first (x) and second (y) fields of each item in dataset.

The text nodes need x and y attributes to position it on the SVG. In this challenge, the y value (which determines height) can use the same value that the circle uses for its cy attribute. The x value can be slightly larger than the cx value of the circle, so the label is visible. This will push the label to the right of the plotted point.

``` html
<body>
  <script>
    const dataset = [
                  [ 34,    78 ],
                  [ 109,   280 ],
                  [ 310,   120 ],
                  [ 79,    411 ],
                  [ 420,   220 ],
                  [ 233,   145 ],
                  [ 333,   96 ],
                  [ 222,   333 ],
                  [ 78,    320 ],
                  [ 21,    123 ]
                ];


    const w = 500;
    const h = 500;

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("circle")
       .data(dataset)
       .enter()
       .append("circle")
       .attr("cx", (d, i) => d[0])
       .attr("cy", (d, i) => h - d[1])
       .attr("r", 5);

    svg.selectAll("text")
       .data(dataset)
       .enter()
       .append("text")
       .text((d) => d[0] + ", " + d[1])
       .attr("x", (d) => d[0] + 5)
       .attr("y", (d) => h - d[1])
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/23_Add_Labels_to_Scatter_Plot_Circles.png">}}

### 24 Create a Linear Scale with D3

The bar and scatter plot charts both plotted data directly onto the SVG. However, if the height of a bar or one of the data points were larger than the SVG height or width values, it would go outside the SVG area.

In D3, there are scales to help plot data. scales are functions that tell the program how to map a set of raw data points onto the pixels of the SVG.

For example, say you have a 100x500-sized SVG and you want to plot Gross Domestic Product (GDP) for a number of countries. The set of numbers would be in the billion or trillion-dollar range. You provide D3 a type of scale to tell it how to place the large GDP values into that 100x500-sized area.

It's unlikely you would plot raw data as-is. Before plotting it, you set the scale for your entire data set, so that the x and y values fit your SVG width and height.

D3 has several scale types. For a linear scale (usually used with quantitative data), there is the D3 method scaleLinear():
const scale = d3.scaleLinear()

``` html
<body>
  <script>
    
    const scale = d3.scaleLinear(); 
    const output = scale(50); 
    
    d3.select("body")
      .append("h2")
      .text(output);

  </script>
</body>
```

### 25 Set a Domain and a Range on a Scale

By default, scales use the identity relationship. This means the input value maps to the output value. However, scales can be much more flexible and interesting.

Say a dataset has values ranging from 50 to 480. This is the input information for a scale, also known as the domain.

You want to map those points along the x axis on the SVG, between 10 units and 500 units. This is the output information, also known as the range.

The domain() and range() methods set these values for the scale. Both methods take an array of at least two elements as an argument. 

``` html
<body>
  <script>
    const scale = d3.scaleLinear();
    scale.domain([250, 500]);
    scale.range([10, 150]);

    const output = scale(50);
    d3.select("body")
      .append("h2")
      .text(output);
  </script>
</body>
```

### 26 Use the d3.max and d3.min Functions to Find Minimum and Maximum Values in a Datasets

The D3 methods domain() and range() set that information for your scale based on the data. There are a couple methods to make that easier.

Often when you set the domain, you'll want to use the minimum and maximum values within the data set. Trying to find these values manually, especially in a large data set, may cause errors.

D3 has two methods - min() and max() to return this information.

``` html
<body>
  <script>
    const positionData = [[1, 7, -4],[6, 3, 8],[2, 9, 3]]
    const minX = d3.min(positionData, (d) => d[0])
    const minY = d3.min(positionData, (d) => d[1])
    const minZ = d3.min(positionData, (d) => d[2])
    const maxX = d3.max(positionData, (d) => d[0])
    const maxY = d3.max(positionData, (d) => d[1])
    const maxZ = d3.max(positionData, (d) => d[2])
    const output = maxZ;

    d3.select("body")
      .append("h2")
      .text(output)
  </script>
</body>
```

### 27 Use Dynamic Scales

Given a complex data set, one priority is to set the scale so the visualization fits the SVG container's width and height. You want all the data plotted inside the SVG so it's visible on the web page

The domain() method passes information to the scale about the raw data values for the plot. The range() method gives it information about the actual space on the web page for the visualization.

In the example, the domain goes from 0 to the maximum in the set. It uses the max() method with a callback function based on the x values in the arrays. The range uses the SVG's width (w), but it includes some padding, too. This puts space between the scatter plot dots and the edge of the SVG.

``` html
<body>
  <script>
    const dataset = [
                  [ 34,    78 ],
                  [ 109,   280 ],
                  [ 310,   120 ],
                  [ 79,    411 ],
                  [ 420,   220 ],
                  [ 233,   145 ],
                  [ 333,   96 ],
                  [ 222,   333 ],
                  [ 78,    320 ],
                  [ 21,    123 ]
                ];

    const w = 500;
    const h = 500;
    const padding = 30;

    const xScale = d3.scaleLinear()
                    .domain([0, d3.max(dataset, (d) => d[0])])
                    .range([padding, w - padding]);
    const yScale = d3.scaleLinear()
                    .domain([0, d3.max(dataset, (d) => d[1])])
                    .range([h - padding, padding])

    const output = yScale(411); // Returns 30
    d3.select("body")
      .append("h2")
      .text(output)
  </script>
</body>
```

### 28 Use a Pre-Defined Scale to Place Elements

With the scales set up, it's time to map the scatter plot again. The scales are like processing functions that turn the x and y raw data into values that fit and render correctly on the SVG. They keep the data within the screen's plotting area.

You set the coordinate attribute values for an SVG shape with the scaling function. This includes x and y attributes for rect or text elements, or cx and cy for circles.

Scales set shape coordinate attributes to place the data points onto the SVG. You don't need to apply scales when you display the actual data value, for example, in the text() method for a tooltip or label.

``` html
<body>
  <script>
    const dataset = [
      [  34,  78 ],
      [ 109, 280 ],
      [ 310, 120 ],
      [  79, 411 ],
      [ 420, 220 ],
      [ 233, 145 ],
      [ 333,  96 ],
      [ 222, 333 ],
      [  78, 320 ],
      [  21, 123 ]
    ];
    
    const w = 500;
    const h = 500;
    const padding = 60;
    
    const xScale = d3.scaleLinear()
      .domain([0, d3.max(dataset, (d) => d[0])])
      .range([padding, w - padding]);
    
    const yScale = d3.scaleLinear()
      .domain([0, d3.max(dataset, (d) => d[1])])
      .range([h - padding, padding]);
    
    const svg = d3.select("body")
      .append("svg")
      .attr("width", w)
      .attr("height", h);
    
    svg.selectAll("circle")
      .data(dataset)
      .enter()
      .append("circle")
      .attr("cx", (d) => xScale(d[0]))
      .attr("cy", (d) => yScale(d[1]))
      .attr("r", 5);
      
    svg.selectAll("text")
      .data(dataset)
      .enter()
      .append("text")
      .text((d) =>  (d[0] + ", " + d[1]))
      .attr("x", (d) => xScale(d[0]+ 10))
      .attr("y", (d) => yScale(d[1]))

  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/28_Use_PreDefined_Scale_To_Place_Elements.png">}}

### 29 Add Axes to a Visualization

Another way to improve the scatter plot is to add an x-axis and a y-axis.

D3 has two methods, axisLeft() and axisBottom(), to render the y-axis and x-axis, respectively. Here's an example to create the x-axis based on the xScale in the previous challenges:

The next step is to render the axis on the SVG. To do so, you can use a general SVG component, the g element. The g stands for group. Unlike rect, circle, and text, an axis is just a straight line when it's rendered. Because it is a simple shape, using g works. The last step is to apply a transform attribute to position the axis on the SVG in the right place. Otherwise, the line would render along the border of the SVG and wouldn't be visible. SVG supports different types of transforms, but positioning an axis needs translate. When it's applied to the g element, it moves the whole group over and down by the given amounts. Here's an example:

``` javascript
const xAxis = d3.axisBottom(xScale);

svg.append("g")
   .attr("transform", "translate(0, " + (h - padding) + ")")
   .call(xAxis);
```

Translate − It takes two options, tx refers translation along the x-axis and ty refers to the translation along the y-axis. For Example− translate(30 30).

The above code places the x-axis at the bottom of the SVG. Then it's passed as an argument to the call() method. The y-axis works in the same way, except the translate argument is in the form (x, 0). Because translate is a string in the attr() method above, you can use concatenation to include variable values for its arguments.

``` html
<body>
  <script>
    const dataset = [
                  [ 34,     78 ],
                  [ 109,   280 ],
                  [ 310,   120 ],
                  [ 79,   411 ],
                  [ 420,   220 ],
                  [ 233,   145 ],
                  [ 333,   96 ],
                  [ 222,    333 ],
                  [ 78,    320 ],
                  [ 21,   123 ]
                ];

    const w = 500;
    const h = 500;
    const padding = 60;

    const xScale = d3.scaleLinear()
                     .domain([0, d3.max(dataset, (d) => d[0])])
                     .range([padding, w - padding]);

    const yScale = d3.scaleLinear()
                     .domain([0, d3.max(dataset, (d) => d[1])])
                     .range([h - padding, padding]);

    const svg = d3.select("body")
                  .append("svg")
                  .attr("width", w)
                  .attr("height", h);

    svg.selectAll("circle")
       .data(dataset)
       .enter()
       .append("circle")
       .attr("cx", (d) => xScale(d[0]))
       .attr("cy",(d) => yScale(d[1]))
       .attr("r", (d) => 5);

    svg.selectAll("text")
       .data(dataset)
       .enter()
       .append("text")
       .text((d) =>  (d[0] + "," + d[1]))
       .attr("x", (d) => xScale(d[0] + 10))
       .attr("y", (d) => yScale(d[1]))

    const xAxis = d3.axisBottom(xScale);
    const yAxis = d3.axisLeft(yScale);

    svg.append("g")
       .attr("transform", "translate(0," + (h - padding) + ")")
       .call(xAxis);

   svg.append("g")
      .attr("transform", "translate("+ padding + ",0)")
      .call(yAxis)
  </script>
</body>
```

{{<figure class="post_image" src="../images/d3js-learning/29_Add_Axes_Visualization.png">}}

## JSON APIs and AJAX

Similar to how UIs help people use programs, APIs (Application Programming Interfaces) help programs interact with other programs. APIs are tools that computers use to communicate with one another, in part to send and receive data.

Programmers often use AJAX (Asynchronous JavaScript and XML) when working with APIs. AJAX refers to a group of technologies that make asynchronous requests to a server to transfer data, then load any returned data into the page. And the data transferred between the browser and server is often in a format called JSON (JavaScript Object Notation).

### 01 Handle Click Events with JavaScript using the onclick property

You want your code to execute only once your page has finished loading. For that purpose, you can attach a JavaScript event to the document called DOMContentLoaded. Here's the code that does this:

``` javascript
document.addEventListener('DOMContentLoaded', function() {});
```

You can implement event handlers that go inside of the DOMContentLoaded function. You can implement an onclick event handler which triggers when the user clicks on the #getMessage element, by adding the following code:

``` javascript
document.getElementById('getMessage').onclick = function(){};
```

### 02 Change Text with click Events

When the click event happens, you can use JavaScript to update an HTML element.

For example, when a user clicks the Get Message button, it changes the text of the element with the class message to say Here is the message.

``` javascript
document.getElementsByClassName('message')[0].textContent="Here is the message";
```

{{<figure class="post_image" src="../images/d3js-learning/02_Change_Text_Click_Events.png">}}

### 03 Get JSON with the JavaScript XMLHttpRequest Method

You can also request data from an external source. This is where APIs come into play.

Remember that APIs - or Application Programming Interfaces - are tools that computers use to communicate with one another. You'll learn how to update HTML with the data we get from APIs using a technology called AJAX.

Most web APIs transfer data in a format called JSON. JSON stands for JavaScript Object Notation.

JSON syntax looks very similar to JavaScript object literal notation. JSON has object properties and their current values, sandwiched between a { and a }.

These properties and their values are often referred to as "key-value pairs".

However, JSON transmitted by APIs are sent as bytes, and your application receives it as a string. These can be converted into JavaScript objects, but they are not JavaScript objects by default. The JSON.parse method parses the string and constructs the JavaScript object described by it.

The JavaScript XMLHttpRequest object has a number of properties and methods that are used to transfer data. First, an instance of the XMLHttpRequest object is created and saved in the req variable. Next, the open method initializes a request - this example is requesting data from an API, therefore is a GET request. The second argument for open is the URL of the API you are requesting data from. The third argument is a Boolean value where true makes it an asynchronous request. The send method sends the request. Finally, the onload event handler parses the returned data and applies the JSON.stringify method to convert the JavaScript object into a string. This string is then inserted as the message text.

``` html
<script>
  const req = new XMLHttpRequest();

  document.addEventListener('DOMContentLoaded', function(){
    document.getElementById('getMessage').onclick = function(){
      req.open("GET",'/json/cats.json',true);
      req.send();
      req.onload = function(){
        const json = JSON.parse(req.responseText);
        document.getElementsByClassName('message')[0].innerHTML  = JSON.stringify(json);
      };
    };
  });
</script>

<style>
  body {
    text-align: center;
    font-family: "Helvetica", sans-serif;
  }
  h1 {
    font-size: 2em;
    font-weight: bold;
  }
  .box {
    border-radius: 5px;
    background-color: #eee;
    padding: 20px 5px;
  }
  button {
    color: white;
    background-color: #4791d0;
    border-radius: 5px;
    border: 1px solid #4791d0;
    padding: 5px 10px 8px 10px;
  }
  button:hover {
    background-color: #0F5897;
    border: 1px solid #0F5897;
  }
</style>

<h1>Cat Photo Finder</h1>
<p class="message box">
  The message will go here
</p>
<p>
  <button id="getMessage">
    Get Message
  </button>
</p>
```

{{<figure class="post_image" src="../images/d3js-learning/03_Get_JSON_JavaScript_XMLHttpRequest_Method.png">}}

### 04 Get JSON with the JavaScript fetch method

Another way to request external data is to use the JavaScript fetch() method. It is equivalent to XMLHttpRequest, but the syntax is considered easier to understand.

Note: The fetch() method uses GET as the default HTTP method. This means you don’t need to specify it explicitly for basic data retrieval.

The first line is the one that makes the request. So, fetch(URL) makes a GET request to the URL specified. The method returns a Promise.

After a Promise is returned, if the request was successful, the then method is executed, which takes the response and converts it to JSON format.

The then method also returns a Promise, which is handled by the next then method. The argument in the second then is the JSON object you are looking for!

Now, it selects the element that will receive the data by using document.getElementById(). Then it modifies the HTML code of the element by inserting a string created from the JSON object returned from the request.

``` html
<script>
  document.addEventListener('DOMContentLoaded',function(){
    document.getElementById('getMessage').onclick= () => {
      fetch('/json/cats.json')
        .then(response => response.json())
        .then(data => {
          document.getElementById('message').innerHTML = JSON.stringify(data);
        })
    };
  });
</script>
```
### 05 Access the JSON Data from an API

```
[ ] -> Square brackets represent an array.
{ } -> Curly brackets represent an object.
" " -> Double quotes represent a string. They are also used for key names in JSON.
```

``` html
<script>
  document.addEventListener('DOMContentLoaded', function(){
    document.getElementById('getMessage').onclick = function(){
      const req = new XMLHttpRequest();
      req.open("GET",'/json/cats.json', true);
      req.send();
      req.onload=function(){
        const json = JSON.parse(req.responseText);
        document.getElementsByClassName('message')[0].innerHTML = JSON.stringify(json);
        console.log(json[2].codeNames[1])
      };
    };
  });
</script>
```

### 06 Convert JSON Data to HTML

You can use a forEach method to loop through the data since the cat photo objects are held in an array. As you get to each item, you can modify the HTML elements.

First, declare an html variable with let html = "";.

Then, loop through the JSON, adding HTML to the variable that wraps the key names in strong tags, followed by the value. When the loop is finished, you render it.

Note: For this challenge, you need to add new HTML elements to the page, so you cannot rely on textContent. Instead, you need to use innerHTML, which can make a site vulnerable to cross-site scripting attacks.

``` html
<script>
  document.addEventListener('DOMContentLoaded', function(){
    document.getElementById('getMessage').onclick = function(){
      const req = new XMLHttpRequest();
      req.open("GET",'/json/cats.json',true);
      req.send();
      req.onload = function(){
        const json = JSON.parse(req.responseText);
        let html = "";
        json.forEach(function(val) {
          const keys = Object.keys(val);
          html += "<div class = 'cat'>";
          keys.forEach(function(key) {
            html += "<strong>" + key + "</strong>: " + val[key] + "<br>";
        });
        html += "</div><br>";
      });
        document.getElementsByClassName('message')[0].innerHTML = html;
      };
    };
  });
</script>

<style>
  body {
    text-align: center;
    font-family: "Helvetica", sans-serif;
  }
  h1 {
    font-size: 2em;
    font-weight: bold;
  }
  .box {
    border-radius: 5px;
    background-color: #eee;
    padding: 20px 5px;
  }
  button {
    color: white;
    background-color: #4791d0;
    border-radius: 5px;
    border: 1px solid #4791d0;
    padding: 5px 10px 8px 10px;
  }
  button:hover {
    background-color: #0F5897;
    border: 1px solid #0F5897;
  }
</style>

<h1>Cat Photo Finder</h1>
<p class="message box">
  The message will go here
</p>
<p>
  <button id="getMessage">
    Get Message
  </button>
</p>
```

{{<figure class="post_image" src="../images/d3js-learning/06_Convert_JSON_Data_HTML.png">}}

### 07 Render Images from Data Sources

The last few challenges showed that each object in the JSON array contains an imageLink key with a value that is the URL of a cat's image.

When you're looping through these objects, you can use this imageLink property to display this image in an img element.

``` javascript
<script>
  document.addEventListener('DOMContentLoaded', function(){
    document.getElementById('getMessage').onclick = function(){
      const req=new XMLHttpRequest();
      req.open("GET",'/json/cats.json',true);
      req.send();
      req.onload = function(){
        const json = JSON.parse(req.responseText);
        let html = "";
        json.forEach(function(val) {
          html += "<div class = 'cat'>";
          html += "<img src = '" + val.imageLink + "' " + "alt='" + val.altText + "'>";
          html += "</div><br>";
        });
        document.getElementsByClassName('message')[0].innerHTML=html;
      };
     };
  });
</script>
```

{{<figure class="post_image" src="../images/d3js-learning/07_Render_Images_from_Data_Sources.png">}}

### 08 Pre-filter JSON to Get the Data You Need

If you don't want to render every cat photo you get from the freeCodeCamp Cat Photo API, you can pre-filter the JSON before looping through it.

Given that the JSON data is stored in an array, you can use the filter method to filter out the cat whose id key has a value of 1.

``` javascript
json = json.filter(function(val) {
  return (val.id !== 1);
});
```

### 09 Get Geolocation Data to Find A User's GPS Coordinates

Another cool thing you can do is access your user's current location. Every browser has a built in navigator that can give you this information.

The navigator will get the user's current longitude and latitude.

You will see a prompt to allow or block this site from knowing your current location. The challenge can be completed either way, as long as the code is correct.

By selecting allow, you will see the text on the output phone change to your latitude and longitude.

First, it checks if the navigator.geolocation object exists. If it does, the getCurrentPosition method on that object is called, which initiates an asynchronous request for the user's position. If the request is successful, the callback function in the method runs. This function accesses the position object's values for latitude and longitude using dot notation and updates the HTML.

```html
<script>
  if (navigator.geolocation){
    navigator.geolocation.getCurrentPosition(function(position) {
      document.getElementById('data').innerHTML="latitude: " + position.coords.latitude + "<br>longitude: " + position.coords.longitude;
    });
  }
</script>
<h4>You are here:</h4>
<div id="data">
</div>
```

### 10 Post Data with the JavaScript XMLHttpRequest Method

In the previous examples, you received data from an external resource. You can also send data to an external resource, as long as that resource supports AJAX requests and you know the URL.

``` javascript
const xhr = new XMLHttpRequest();
xhr.open('POST', url, true);
xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
xhr.onreadystatechange = function () {
  if (xhr.readyState === 4 && xhr.status === 201){
    const serverResponse = JSON.parse(xhr.response);
    document.getElementsByClassName('message')[0].textContent = serverResponse.userName + serverResponse.suffix;
  }
};
const body = JSON.stringify({ userName: userName, suffix: ' loves cats!' });
xhr.send(body);
```