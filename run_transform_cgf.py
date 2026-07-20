from transform_cgf import transform_cgf

INPUT = "DMCH_cash_S8EV_Hand.cgf"
OUTPUT = "D:\EA dev\Objects\pc\dm\mesh"


def main():
    transform_cgf(input=INPUT, model="lf")
    # transform_cgf(INPUT, OUTPUT, , model="lf")


if __name__ == "__main__":
    main()
