#include <string>
#include <iostream>
#include <iomanip>
#include <yarp/os/all.h>
#include <yarp/sig/all.h>
#include <map>


#include "behavior.h"

using namespace std;
using namespace yarp::os;
using namespace yarp::sig;



class Reactions: public Behavior
{
private:
    void run(Bottle args=Bottle());
    
public:
    Reactions(Mutex* mut): Behavior(mut) {
        ;
    }
       
    void configure();

    void close_extra_ports() {
        ;
    }
};