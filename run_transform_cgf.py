from transform_cgf import transform_cgf

INPUT = "LFCL_Cash_casualrider1111_body.cgf"
OUTPUT = "D:\EA dev\Objects\pc\lf\mesh"


def main():
    transform_cgf(input=INPUT, model="lf")
    # transform_cgf(INPUT, OUTPUT, , model="lf")


if __name__ == "__main__":
    main()
