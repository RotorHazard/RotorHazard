import tkinter as tk

def yesornowindow(label = '', title = ''):
    
    # this class is just for getting info out of the button
    class Buttonoutput(object):
        def __init__(self,):
            self.yesorno = ''
            
        def buttoninput(self, answer):
            self.yesorno = answer
    
    #make the button output object
    buttonanswer = Buttonoutput()    

    #for assigning data to the button output object
    def clickyes():
        buttonanswer.buttoninput('y')
    def clickno():
        buttonanswer.buttoninput('n')
 
    #Create an instance of Tkinter frame
    win= tk.Tk()

    #Set the geometry of Tkinter frame
    win.geometry("750x250")
    
    #set window color
    win.configure(bg='light grey')
    
    #set the window title
    win.title(title)

    #Initialize a Label to display the User Input
    label= tk.Label(win, text=label, font=("Courier 10 bold"), background = 'light grey')
    label.pack()

    #Create a Button to validate Entry Widget
    tk.Button(win, text= "Yes",width= 20, command=
              lambda:[clickyes(), win.destroy()]).pack(padx = 100, side = 'left')
    tk.Button(win, text= "No",width= 20, command=
              lambda:[clickno(), win.destroy()]).pack(padx = 100, side = 'right')
      
    win.mainloop()
    
    return buttonanswer.yesorno
    
#print(yesornowindow('enter name here'))