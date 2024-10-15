from models import *


async def get_product():
    products = await product_pydantic.from_queryset(Product.all())
    return {
        'status': 'ok',
        'data': products
    }

async def create_product(product: product_pydanticIn, user: user_pydantic): # type: ignore
    # Fetch the actual User ORM object (await it)
    user_obj = await User.get(id=user.id)
    
    # Get the Business associated with the user (await it)
    business = await Business.get(owner=user_obj)

    # Prepare the product data for creation
    product_info = product.dict(exclude_unset=True)
    product_info['business'] = business

    # Create the new product (await the ORM call)
    product_obj = await Product.create(**product_info)

    # Convert the newly created product to Pydantic format (await this too)
    new_product = await product_pydantic.from_tortoise_orm(product_obj)

    return {
        'status': 'ok',
        'data': new_product
    }